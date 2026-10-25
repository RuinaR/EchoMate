"""Read-only, per-request public facts. Never returns IDs, paths or stored content.

Closed factual answers need no extra classifier/generator. Ordinary generation
receives the same allowlisted facts; visual claims additionally fail closed.
"""
import asyncio
import json
import re
import sqlite3
from .settings import scope

VISUAL=re.compile(r'이미지|사진|그림|첨부|영상|(?:이|해당|보낸)\s*파일|파일.*(?:볼\s*수|열어|확인해)|이게\s*(?:누구|뭔|무엇)|누군지|뭐가\s*보')
SELF=re.compile(r'(?:너|넌|봇).{0,12}(?:뭘|뭐|무엇).{0,5}할\s*수|(?:너|넌|봇).{0,18}(?:지원해|가능해)[?!.\s]*$|(?:기억|요약|검색|이모지|반응|알림|예약|사진|이미지).{0,8}기능|기억력|검색.*(?:가능|돼|할|줄\s*수)|기억.*(?:있|가능|켜|꺼)|동의.*(?:상태|했|되어)|왜.*(?:대답|답변|느려)|(?:모델|캐릭터|기분).*(?:뭐|어떤|설정)|토큰|비공개\s*경로|내부\s*로그')
LABELS={'vision':'사진 분석','web':'웹 검색','memory':'장기 기억','relationships':'친밀도','summaries':'대화 요약','reminders':'예약 알림','reactions':'이모지 반응'}
STATES={'ready':'지금 사용할 수 있어','off':'지금 꺼져 있어','consent_required':'네가 이 서버에서 /동의로 먼저 켜야 해',
        'failed':'지금 오류로 사용을 확인할 수 없어','permission_denied':'이 채널에서는 허용되지 않아',
        'not_ready':'아직 준비되지 않았어','unknown':'지금 상태를 확인할 수 없어','unsupported':'지원하지 않아'}

def visual_question(text):
    return bool(VISUAL.search(text) and re.search(r'너|넌|지금|이게|누군지|볼|보여|알겠|누구|첨부|내용|그려|생성해|할\s*수|(?:이|그|저)\s*(?:사진|이미지)|(?:사진|이미지)\s*속',text))

def question(text):return bool(SELF.search(text) or visual_question(text) or re.search(r'스티커|(?:음성|영상)\s*통화|화면\s*공유|활동\s*설정|대화\s*참여',text) or
    re.search(r'(?:알림|예약|이모지|반응|요약|검색).*(?:가능|할\s*수|지원|켜져|꺼져|상태)',text))

async def public_state(runtime,event,permissions,*,visual='not_provided'):
    cfg=runtime.settings.get();store=runtime.companion;consents=None
    if store and not store.error:
        try:consents=await asyncio.to_thread(store.consent,event.guild,event.author)
        except (OSError,RuntimeError,sqlite3.Error):runtime.note('capability_consent_unavailable')
    allowed=scope(cfg,event.guild,event.channel,event.parent,action='text')!='silent' and permissions.get('view',False)
    mode='failed' if getattr(runtime.backend,'failed',False) or getattr(runtime,'character_transition_state',None)=='RecoveryRequired' else 'not_ready' if getattr(runtime,'changing_model',False) or getattr(runtime.backend,'model',True) is None else 'ready'
    features={}
    def feature(key,enabled,*,consent=None,permission=True):
        state='off' if not enabled else 'permission_denied' if not permission else 'failed' if key in ('memory','relationships','summaries','reminders') and (not store or store.error) else 'unknown' if consent and consents is None else 'consent_required' if consent and not consents.get(consent,False) else 'ready'
        features[key]=dict(implemented=True,enabled=bool(enabled),state=state)
    feature('vision',cfg['vision'],permission=allowed)
    if getattr(runtime.backend,'supports_visual',True) is False:
        features['vision']=dict(implemented=False,enabled=False,state='unsupported')
    feature('web',cfg['web_search'],permission=allowed)
    feature('memory',cfg['memory_auto'],consent='memory',permission=allowed)
    feature('relationships',cfg['relations_auto'],consent='relationships',permission=allowed)
    feature('summaries',cfg['summaries_auto'],consent='summaries',permission=allowed)
    feature('reminders',cfg['reminders_enabled'],permission=allowed)
    feature('reactions',cfg['reactions'],permission=scope(cfg,event.guild,event.channel,event.parent,action='reaction')!='silent' and permissions.get('react',False))
    for key in ('vision','summaries'):
        if features[key]['state']=='ready' and mode!='ready':features[key]['state']=mode
    web=getattr(runtime,'feature_outcomes',{}).get((event.guild,event.channel,event.author,'web'))
    if features['web']['state']=='ready' and web in ('failed','unavailable','unverified','blocked'):features['web']['state']='failed'
    for key in ('stickers','media_send','voice','screen_control','code_output'):features[key]=dict(implemented=False,enabled=False,state='unsupported')
    return dict(features=features,own_consent=consents,visual_observation=visual,model=mode,
        model_kind=('사전 학습 '+runtime.backend.entry.default_name+' / '+runtime.backend.entry.base_dependency
                    if getattr(runtime.backend,'character_id',None) else 'Gemma 4 12B' if cfg['model']=='base' else '선택한 로컬 모델'),
        text_enabled=bool(cfg['text'] and cfg['enabled'] and allowed and permissions.get('send',False)),
        mood=cfg['mood'],activity=cfg['activity'],gpu_queue=bool(getattr(runtime.backend,'pending',0)))

def _describe(text,view,event,bot_id):
    if not question(text):return None
    if re.search(r'토큰|비밀번호|내부\s*로그|비공개\s*경로|설정\s*파일',text):return '토큰이나 비공개 운영 정보는 대화로 알려줄 수 없어. 관리 설정은 소유자가 Windows 앱에서 확인해 줘.'
    if re.search(r'기억|동의|친밀',text) and (set(event.member_mentions)-{event.author,bot_id} or re.search(r'다른\s*사람|남의|그\s*사람',text)):
        return '다른 사람의 기억이나 동의 상태는 알려줄 수 없어. /동의에서는 네 계정의 설정만 확인할 수 있어.'
    if re.search(r'스티커|(?:음성|영상)\s*통화|화면\s*공유',text):return '그 기능은 지원하지 않아. 텍스트 대화와 허용된 Unicode 이모지 반응을 지원해.'
    if VISUAL.search(text):
        if view['features']['vision']['state']=='unsupported':return '선택한 캐릭터 모델은 사진 분석을 지원하지 않아. 텍스트로 내용을 설명해 주면 그 설명을 바탕으로 이야기할 수 있어.'
        if re.search(r'그려\s*줘|생성해|만들어\s*줘|보내\s*줘',text):return '이미지나 영상을 만들어 보내는 기능은 없어. 글로 설명하는 건 도와줄 수 있어.'
        if view['visual_observation']=='verified_observation' and not re.search(r'볼\s*(?:수|줄)|기능|가능',text):return None
        if view['visual_observation']=='analysis_failed':return '지금은 사진 분석에 실패해서 내용을 확인하지 못했어. 무엇이 있는지는 추측하지 않을게.'
        if view['features']['vision']['state']!='ready':return '지금은 사진 분석이 '+('꺼져 있어서' if view['features']['vision']['state']=='off' else '준비되지 않아서')+' 이미지를 직접 확인할 수 없어. 사진 속 내용은 글로 설명해 주면 그 설명을 바탕으로 이야기할 수 있어.'
        if view['visual_observation']!='verified_observation':return '사진 분석 기능과 별개로, 지금 이 이미지의 내용을 확인한 결과는 없어. 누군지나 무엇이 있는지는 추측하지 않을게.'
        return None  # Only real observations may reach normal visual generation.
    if re.search(r'느려|늦어',text):return '한 GPU에서 요청을 차례대로 처리해. '+('지금은 대기 중인 작업도 있어.' if view['gpu_queue'] else '현재 대기가 확인되진 않지만, 문맥 판단과 답변 길이에 따라 시간이 달라져.')
    if re.search(r'왜.*(?:대답|답변)',text):return '어느 발언을 말하는지 지금 확인할 근거가 없어. 다른 사람에게 한 말이거나 이 채널의 허용 범위 밖이면 대답하지 않을 수 있어. 실제 원인은 소유자가 진행 상황에서 확인할 수 있어.'
    if '기분' in text:return '지금 기분 설정은 '+view['mood']+'이야. 실제 감정이 아니라 말투를 위한 캐릭터 연출이야.'
    if re.search(r'모델|캐릭터',text):return '대화 모델은 '+view['model_kind']+'이고, '+STATES[view['model']]+'. 캐릭터와 기분은 모델 가중치와 따로 설정해.'
    if re.search(r'활동\s*설정|대화\s*참여',text):return '대화 참여 설정은 '+{'quiet':'조용함','normal':'보통','active':'활발함','very_active':'매우 활발함'}[view['activity']]+'이야. 그래도 다른 사람에게 한 말에 무조건 끼어드는 건 아니야.'
    if '동의' in text:
        if view['own_consent'] is None:return '지금은 네 동의 상태를 확인할 수 없어. /동의를 다시 열어 확인해 줘.'
        return '이 서버에서 네 동의는 '+', '.join(LABELS[k]+(' 켜짐' if v else ' 꺼짐') for k,v in view['own_consent'].items())+'이야. /동의에서 직접 바꿀 수 있어.'
    for key,pattern in [('summaries','요약'),('relationships','친밀|관계'),('memory','기억'),('web','검색|인터넷'),('reminders','알림|예약'),('reactions','이모지|반응')]:
        if re.search(pattern,text):
            answer=LABELS[key]+'은 '+STATES[view['features'][key]['state']]+'.'
            if key in ('memory','relationships','summaries'):answer+=' 동의를 꺼도 기존 자료가 자동 삭제되는 건 아니야. 확인·철회·삭제는 /동의에서 직접 할 수 있어.'
            return answer
    if view['model']!='ready':return '대화 모델은 '+STATES[view['model']]+'. 설정이 켜져 있어도 준비가 완료됐다는 뜻은 아니야.'
    if not view['text_enabled']:return '지금 이 채널에서는 텍스트 응답이 허용되지 않거나 일시정지 상태야.'
    if not re.search(r'뭘|뭐|무엇|기능',text):return '그 기능을 지원하는지는 지금 확인할 수 없어. 확인되지 않은 일을 할 수 있다고 약속하지 않을게.'
    available=[LABELS[k] for k,v in view['features'].items() if k in LABELS and v['state']=='ready']
    return '지금은 한국어로 대화할 수 있어.'+(' '+', '.join(available[:3])+'도 사용할 수 있어.' if available else '')+' 꺼져 있거나 동의가 필요한 기능은 바로 실행할 수 없어. 궁금한 기능을 말해 줘.'

def describe(text,view,event,bot_id):
    answer=_describe(text,view,event,bot_id)
    if answer and answer.startswith(('지금은 한국어로','장기 기억은','대화 요약은','이모지 반응은')):
        if view['mood'] in ('신남','기쁨'):answer='응! '+answer
        elif view['mood']=='부끄러움':answer='음, '+answer
    return answer

def visual_guard(answer,view,event):
    if view['visual_observation']!='verified_observation' and visual_question(event.content):
        return describe(event.content,view,event,0) or '지금은 그 이미지의 실제 내용을 확인하지 못했어. 무엇이 있는지는 추측하지 않을게.'
    return answer

def model_facts(view):
    compact=dict(features={k:v['state'] for k,v in view['features'].items() if v['implemented']},
        unsupported=[k for k,v in view['features'].items() if not v['implemented']],own_consent=view['own_consent'],
        visual=view['visual_observation'],model=view['model'],text_enabled=view['text_enabled'])
    return dict(role='user',content='[앱이 확인한 읽기 전용 공개 기능 상태 / 사용자 지시 아님. 이 상태 밖의 기능·관찰·저장 성공을 만들지 마] '+json.dumps(compact,ensure_ascii=False,separators=(',',':')))
