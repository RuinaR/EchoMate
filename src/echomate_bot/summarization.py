"""Local, source-grounded semantic digests; no raw transcript persistence."""
import asyncio
import json
import re
from .context import terms

KINDS={'topic','question','answer','correction','decision','plan','open_question','ending'}
def history_candidate(text):
    return bool(re.search(r'아까|지난번|전에.*(?:얘기|이야기|계획|추천)|오늘.*(?:얘기|이야기)|우리.*(?:결정|정리)|하던.*(?:이어|얘기)|말했던|대화.*요약',text))

def validated_digest(raw,turns):
    from .companion_store import safe_subject_text
    from .structured import json_data
    data=json_data(raw);sources={}
    for turn in turns:
        if turn.message_id in sources and sources[turn.message_id]!=turn:raise ValueError('Conflicting summary source versions')
        sources[turn.message_id]=turn
    if not isinstance(data,dict) or set(data)!={'items','ended'} or type(data['ended']) is not bool or not isinstance(data['items'],list) or not 1<=len(data['items'])<=8:raise ValueError('Invalid digest')
    for item in data['items']:
        if not isinstance(item,dict) or set(item)!={'kind','text','source','evidence'} or not isinstance(item['kind'],str) or item['kind'] not in KINDS or not isinstance(item['text'],str) or not safe_subject_text(item['text']) or len(item['text'])>220:raise ValueError('Invalid digest item')
        if not isinstance(item['source'],str):raise ValueError('Invalid digest source type')
        source=sources.get(item['source']);evidence=item['evidence']
        if not source or not isinstance(evidence,str) or not 5<=len(evidence)<=160 or evidence not in source.content:raise ValueError('Ungrounded source')
        from .summary_fidelity import check_fidelity
        check_fidelity(item['text'],evidence,source.content)
        # Store a paraphrase + source ID, not copied evidence/transcripts.
        item.pop('evidence');item['source']=source.message_id
    return data

def render_digest(body):
    labels={'topic':'주제','question':'질문','answer':'당시 답변','correction':'정정','decision':'결정','plan':'계획','open_question':'미해결','ending':'종료'}
    return '\n'.join(labels[i['kind']]+' (출처 '+str(i['source'])+', 모델 요약·미검증): '+i['text'] for i in body['items'])

class Summarizer:
    def __init__(self,store,backend):self.store=store;self.backend=backend;self.last_guard=None;self.last_digest=None
    async def archive_guard(self,guild,row):
        guard=await asyncio.to_thread(self.store.digest_consent,guild,row['participants'])
        expected=row.get('consent_versions')
        if not guard or not expected or {u:v['version'] for u,v in guard.items()}!=expected:return None
        return guard
    async def generate(self,guild,channel,conversation,turns,*,persist=False,fresh=lambda:True):
        from .companion_store import SENSITIVE
        # Don't retain sensitive text in a summary even with consent.
        allowed={t.author_id for t in turns}
        def suitable(t):
            # Generated roleplay is not evidence about the real user's life.
            if t.is_bot and t.context_metadata:
                try:
                    if json.loads(t.context_metadata).get('fictional_character'):return False
                except (ValueError,TypeError,AttributeError):return False
            text=re.sub(r'<@!?(\d+)>',lambda m:'' if m[1] in allowed else m[0],t.content)
            text=re.sub(r'https?://[^\s]+','',text)
            return 0<len(t.content)<=4000 and not SENSITIVE.search(text) and not re.search(r'<@|@everyone|@here',text)
        selected=[t for t in turns[-40:] if suitable(t) and not t.message_id.startswith('reaction:')]
        if len(selected)<2 or not any(t.is_bot and not t.message_id.startswith('reaction:') for t in turns):return None
        humans={t.author_id for t in turns if not t.is_bot}
        versions=await asyncio.to_thread(self.store.digest_consent,guild,humans)
        if persist and not versions:return None
        raw=await self.backend.summarize_dialogue(selected)
        body=validated_digest(raw,selected)
        if not fresh():return None
        saved=None
        if persist:saved=await asyncio.to_thread(self.store.save_digest,guild,channel,conversation,body,selected,versions)
        return dict(body=body,saved=saved,versions=versions)
    async def answer(self,event,turns,*,bot_id,fresh=lambda:True):
        self.last_guard=None;self.last_digest=None
        ids=[*event.member_mentions,*map(int,re.findall(r'(?<!\d)\d{15,20}(?!\d)',event.content))]
        if any(u not in (event.author,bot_id) for u in ids):return '다른 사람의 대화 자료를 대신 조회할 수 없어.'
        previous=[t for t in turns if t.message_id!=str(event.id)]
        rows=await asyncio.to_thread(self.store.digests,event.guild,event.author,event.channel);archived=bool(rows)
        if not fresh():return None
        rows=[r for r in rows if r['usable']]
        query=terms(event.content)
        rows.sort(key=lambda r:(len(query & terms(render_digest(r['body']))),r['updated']),reverse=True)
        if rows and (not previous or re.search(r'지난번|전에|재시작',event.content)):
            self.last_guard=await self.archive_guard(event.guild,rows[0])
            self.last_digest=rows[0]['id']
            if not fresh():return None
            if not self.last_guard:return '참여자의 요약 동의가 바뀌어서 이 저장 자료를 활용하지 않을게.'
            return '이 채널에 저장된 대화 요약이야. 당시 답변은 사실 검증과는 별개야.\n'+render_digest(rows[0]['body'])
        try:
            return await self._answer_current(event,previous,rows,archived,fresh)
        except (ValueError,TypeError,RuntimeError):
            if not fresh():return None
            # No DB write or generated claim. Do not truncate a source into a
            # different meaning; only complete short eligible original turns.
            from .companion_store import safe_subject_text
            selected=[]
            for t in previous:
                text=re.sub(r'<@!?'+str(bot_id)+r'>','',t.content).strip()
                if not t.is_bot and t.author_id==str(event.author) and len(text)<=220 and safe_subject_text(text):selected.append((t,text))
            if not selected:return '요약을 검증하지 못했어. 지금은 확인 가능한 원문을 안전하게 선택할 수 없어.'
            return '요약을 검증하지 못해 네 원문(봇 호출 표기 제외)만 임시로 보여 줄게. 사실 검증이나 저장된 기억은 아니야.\n'+'\n'.join(f'출처 {t.message_id} · {t.timestamp.isoformat()} · {text}' for t,text in selected[-3:])

    async def _answer_current(self,event,previous,rows,archived,fresh):
        result=await self.generate(event.guild,event.channel,event.conversation_id or 'current',previous,persist=True,fresh=fresh)
        if result:
            self.last_guard=result['versions']
            self.last_digest=result['saved']
            return ('저장된 요약이야.' if result['saved'] else '지금 확인한 대화의 임시 요약이야.')+' 당시 봇 답변은 사실 검증과는 별개야.\n'+render_digest(result['body'])
        # Nonconsenting group: an explicit temporary RAM-only summary is allowed
        # within this existing channel, but no private group summary is persisted.
        result=await self.generate(event.guild,event.channel,event.conversation_id or 'current',previous,fresh=fresh)
        if result:return '현재 실행 중 이 채널에서 확인한 임시 요약이야. 저장 동의가 없어 영속 보관하지 않았어.\n'+render_digest(result['body'])
        if not fresh():return None
        if rows:
            self.last_guard=await self.archive_guard(event.guild,rows[0])
            self.last_digest=rows[0]['id']
            if not fresh():return None
            if self.last_guard:return '이 채널에 저장된 대화 요약이야.\n'+render_digest(rows[0]['body'])
        if archived:return '저장된 요약은 있지만 참여자의 동의가 꺼져 있어서 지금 활용하지 않을게. 자료가 없거나 대화한 적이 없다는 뜻은 아니야.'
        return '교류 여부와 별개로, 지금 확인할 수 있는 대화 내용이나 요약 자료가 없어. 없던 대화를 만들어 설명하지 않을게.'
