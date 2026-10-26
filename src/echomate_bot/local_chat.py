"""Credential-free local test runtime. Only its own synthetic v8 store is opened.

Structured commands reuse production Store/receipts. Free text never mutates
memory or reminders. This is not Discord social qualification or delivery.
"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
import re
import sqlite3
import time
import threading

from .character_store import CharacterStores
from .companion import handle_request, operation_failure, request_plan
from .operation_receipts import read_receipt, MemorySelection, read_values
from .runtime import Event
from .settings import DEFAULTS, atomic_private_json, private_path
from .lookup_inquiries import lookup_state_answer

# Task-local, never shared across requests/users or enabled by Discord traffic.
stream_observer = ContextVar('local_chat_stream_observer', default=None)
local_token_budget = ContextVar('local_chat_token_budget', default=False)


class LocalChat:
    def __init__(self, root):
        self.root = private_path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root/'synthetic.sqlite3'
        self.hub = CharacterStores(path) if path.exists() else CharacterStores.create(path)
        self.store = self.hub.for_character('lime')
        self.histories = {}
        self.history_signatures = {}
        self.rows = []
        self.partial = ''
        self.status = 'idle'
        self.epoch = 0
        self.lock = asyncio.Lock()
        self.last = {}
        self.active_reads = {}
        self.operations = []
        self.scope = (2, 3, 4)
        self.notification_service_failed=False
        self.version_lock=threading.Lock()
        version_path=self.root/'state-version.json'
        self.version=json.loads(version_path.read_text('utf-8')) if version_path.exists() else 0
        if type(self.version) is not int or self.version<0:raise ValueError('Invalid local state version')

    def touch(self):
        # Persist before mutation. A saved conversation cannot resurrect facts
        # after local consent/forget/correction, even across app restarts.
        with self.version_lock:
            atomic_private_json(self.root/'state-version.json',self.version+1)
            self.version+=1

    def snapshot(self):
        return dict(rows=[dict(r) for r in self.rows[-200:]], partial=self.partial,
                    status=self.status, last=dict(self.last), scope=self.scope,
                    mode='LOCAL_CHAT', synthetic=True,read_execution={k:r.public() for k,r in self.active_reads.items()} if self.status=='generating' else self.last.get('reads',{}),notification_service='FAILED' if self.notification_service_failed else 'RUNNING')

    def reset(self):
        self.epoch += 1
        self.histories.clear()
        self.history_signatures.clear()
        self.rows=[r for r in self.rows if r.get('notification_id') and not r.get('acknowledged')]
        self.partial = ''
        # Reset conversation does not delete explicitly saved test memories.
        self.status='idle';self.last={}

    def stream(self, kind, value):
        self.partial = '' if kind == 'reset' else (self.partial+value)[-100000:]

    @staticmethod
    def receipt_fact(receipt):
        labels={'memory_saved':'기억 저장 성공','memory_cleared':'기억 삭제 완료·자동 저장 중단',
                'memory_removed':'기억 항목 제거 완료','memory':'이번 허용 범위 기억 목록 조회 성공',
                'reminders':'이 채널 본인 알림 목록 조회 성공'}
        fact=dict(kind=receipt.kind,outcome='SUCCESS',meaning=labels.get(receipt.kind,receipt.kind))
        if receipt.kind=='reminder':
            values=dict(receipt.values)
            fact['status']=values['status']
            fact['meaning']='알림 예약 성공' if fact['status']=='scheduled' else '알림 취소 완료'
            # The caller already checked scope/current(). Preserve bounded
            # receipt data, not just a success label; payload is not an instruction.
            text=values['text']
            fact.update(request_text=text[:120],request_text_truncated=len(text)>120,
                        due_at=values['due_at'],timezone=values['timezone'])
        elif receipt.kind in ('memory','reminders'):
            fact['result_count']=len(receipt.values)
        return fact

    def save(self):
        atomic_private_json(self.root/'session.json', dict(schema=2,state_version=self.version,
            histories=[dict(scope=list(k), messages=v,signature=self.history_signatures.get(k)) for k,v in self.histories.items()], rows=self.rows[-200:]))

    def restore(self):
        path=self.root/'session.json'
        if path.stat().st_size > 4*1024**2:
            raise ValueError('Local session exceeds limit')
        value=json.loads(path.read_text('utf-8'))
        histories={}
        if (value.get('schema')!=2 or value.get('state_version')!=self.version or
            not isinstance(value.get('histories'),list) or len(value['histories'])>8):
            raise ValueError('Invalid local session')
        for item in value['histories']:
            scope=tuple(item['scope']);self.validate_scope(scope)
            if item.get('signature')!=self.state_signature(scope):raise ValueError('Saved session evidence changed')
            messages=item['messages']
            if not isinstance(messages,list) or len(messages)>400:
                raise ValueError('Local history exceeds limit')
            for i,message in enumerate(messages):
                if (set(message)!={'role','content'} or message['role']!=('user' if i%2==0 else 'assistant') or
                    not isinstance(message['content'],str) or len(message['content'])>8000):
                    raise ValueError('Invalid local history role/content')
            if len(messages)%2 or scope in histories:
                raise ValueError('Unpaired/duplicate local history')
            histories[scope]=messages
        # Untrusted saved display rows cannot introduce a policy/system role.
        rows=value.get('rows',[])
        if not isinstance(rows,list) or len(rows)>200:
            raise ValueError('Invalid local display history')
        for row in rows:
            if (not isinstance(row,dict) or row.get('role') not in ('user','assistant') or
                not isinstance(row.get('text'),str) or len(row['text'])>8000):
                raise ValueError('Invalid local display row')
            self.validate_scope(tuple(row.get('scope',())))
        # Saved text is never an executable notification acknowledgement.
        rows=[dict(role=row['role'],text=row['text'],scope=list(row['scope'])) for row in rows]
        rows.extend(row for row in self.rows if row.get('notification_id') and not row.get('acknowledged'))
        self.epoch+=1;self.histories=histories;self.rows=rows[-200:];self.partial=''
        self.history_signatures={scope:self.state_signature(scope) for scope in histories}

    def state_signature(self,scope):
        """Read-only local provenance, never a model input or permission grant."""
        g,ch,u=map(str,scope);digest=hashlib.sha256()
        with self.store.db() as db:
            db.execute('BEGIN')
            for sql,args in (
                ('SELECT * FROM consent_choices WHERE guild=? AND user=? ORDER BY category',(g,u)),
                ('SELECT * FROM relationships WHERE guild=? AND user=?',(g,u)),
                ('SELECT * FROM memories WHERE guild=? AND user=? AND channel=? ORDER BY memory_id',(g,u,ch)),
                ('SELECT * FROM reminders WHERE guild=? AND requester=? AND channel=? ORDER BY reminder_id',(g,u,ch))):
                for row in db.execute(sql,args):digest.update(json.dumps(dict(row),sort_keys=True,ensure_ascii=False).encode())
        return digest.hexdigest()

    @staticmethod
    def validate_scope(scope):
        if tuple(scope) not in ((2,3,4),(2,3,5),(2,6,4),(2,6,5)):
            raise ValueError('Only synthetic local users/channels are supported')

    def clear_subject_context(self, scope):
        for key in list(self.histories):
            if key[0]==scope[0] and key[2]==scope[2]:self.histories.pop(key);self.history_signatures.pop(key,None)
        self.operations=[item for item in self.operations if item['scope'][0]!=scope[0] or item['scope'][2]!=scope[2]]

    def operation_help(self,text):
        """Explain the existing local command boundary; never execute prose.

        Reuse the production request plan. Only a narrow present capability
        question supplements it; reports/conditions and casual futures remain
        conversation. This is not a generated-claim detector.
        """
        plan=request_plan(text)
        kind=plan.kind if plan is not None else None
        from .intent_router import plan_intent,IntentMode
        if kind and plan_intent(text,kind).mode not in (IntentMode.REQUEST,IntentMode.CLARIFY):kind=None
        if kind not in ('reminder','memory'):
            from .intent_router import request_clauses
            for clause in request_clauses(text):
                if re.search(r'라고|다고|다면|라면|만약|인용|친구',clause):continue
                if (re.search(r'알림|예약',clause) and
                    re.search(r'(?:할\s*수\s*있(?:어|니)|가능(?:해|하니)|지원(?:해|하니))\s*$',clause)):
                    kind='reminder';break
        if kind=='reminder':
            if self.notification_service_failed:return '로컬 알림 서비스에 오류가 있어 지금 사용할 수 없어. 이번 응답으로 예약을 실행하지 않았어.'
            return '로컬 테스트는 /알림 명령으로 예약해. 예: /알림 30분 후 물 마시라고 알려줘. 일반 대화만으로는 등록하지 않았어. 목록은 /알림 목록에서 확인할 수 있어.'
        if kind=='memory':
            return '로컬 테스트의 기억 조회·저장·수정·삭제는 /기억 명령을 사용해. 저장에는 본인의 /동의 기억 켜기가 먼저 필요해. 이번 응답으로 기억을 변경하지 않았어.'
        return None

    def command(self,text,scope,outcomes=None):
        """Explicit local-only grammar; quotes/proposals are not tool calls."""
        g,ch,u=scope
        self.touch()
        if text.startswith('/동의 '):
            _,category,choice=text.split()
            key={'기억':'memory','관계':'relationships'}[category]
            if choice not in ('켜기','끄기'):raise ValueError('동의: 켜기 또는 끄기')
            self.store.set_consent(g,u,key,choice=='켜기');self.epoch+=1
            # Old context must not re-introduce consent-revoked information.
            self.clear_subject_context(scope)
            return '테스트 '+category+' 동의를 '+choice+'로 적용했어.', [], 'SUCCESS'
        if text.startswith('/친밀도 '):
            value=float(text.split(maxsplit=1)[1]);self.store.set_affinity(g,u,value,require_consent=True)
            self.epoch+=1
            return '합성 사용자의 테스트 친밀도를 적용했어.', [], 'SUCCESS'
        if self.notification_service_failed and text.startswith('/알림 ') and not text.startswith(('/알림 목록','/알림 취소')):
            return '로컬 알림 기능은 지원하지만 처리 서비스가 중단됐어. 지금은 새 예약을 실행하지 않을게. 앱을 재시작해 확인해 줘.', [], 'NOT_EXECUTED'
        body=None
        if text.startswith('/기억 정정 '):
            _,_,key,summary=text.split(maxsplit=3)
            rows=[r for r in self.store.memories(g,u,ch) if r['memory_id'].startswith(key)]
            if len(key)<8 or len(rows)!=1:raise ValueError('본인 기억의 앞8자리 번호가 필요해요')
            row=rows[0]
            self.store.edit_memory(g,row['memory_id'],summary,row['expires_at'],'active')
            current=self.store.memories(g,u,ch)[:3]
            event=Event(1,g,ch,u,text,datetime.now(timezone.utc))
            receipt=read_receipt('memory',event,current,self.store.subject_snapshot(g,u),character_id='lime')
            if not receipt.current(self.store):raise RuntimeError('Memory changed')
            self.epoch+=1;self.clear_subject_context(scope)
            return '테스트 기억을 정정했어.',[receipt],'SUCCESS'
        if text.startswith('/작업 '):body=text[len('/작업 '):]
        elif text.startswith('/기억 저장 '):body='기억해 줘 '+text[len('/기억 저장 '):]
        elif text=='/기억 목록':body='내 기억 목록 보여줘'
        elif text=='/기억 삭제':body='내 기억 삭제해 줘'
        elif text.startswith('/알림 '):body='알림 '+text[len('/알림 '):]
        if body is None:
            return ('로컬 명령: /동의 기억|관계 켜기|끄기, /기억 저장 내용, /기억 목록, /기억 정정 앞8자리 내용, /기억 삭제, '
                    '/친밀도 0~100, /알림 10분 후 물 마시라고 알려줘, /알림 목록, /알림 취소 번호, '
                    '/작업 명확한 조회와 알림 요청'), [], 'NOT_EXECUTED'
        receipts=[]
        event=Event(int(time.time_ns()),g,ch,u,body,datetime.now(timezone.utc),conversation_id='local')
        cfg=deepcopy(DEFAULTS);cfg['guilds']={str(g):dict(timezone='Asia/Seoul')}
        try:
            result=handle_request(self.store,event,cfg,999,receipts=receipts,outcomes=outcomes)
        except (OSError,RuntimeError,ValueError,sqlite3.Error):
            return operation_failure(request_plan(body)), [], 'FAILED'
        if not all(r.current(self.store) for r in receipts):
            return '근거가 바뀌어 완료 상태를 확인할 수 없어.', [], 'UNKNOWN'
        if text=='/기억 목록' and receipts:
            rows=[dict(row) for row in receipts[0].values]
            if rows:result='테스트 기억(정정 시 앞8자리 사용):\n'+'\n'.join(r['memory_id'][:8]+' · '+r['summary'] for r in rows)
        self.epoch+=1
        # No stale facts from a pre-delete/correction prompt are re-used.
        self.clear_subject_context(scope)
        from .companion import outcome_state
        return result or '실행할 기능을 확인하지 못했어.', receipts, outcome_state(outcomes) if outcomes else 'SUCCESS' if receipts else 'NOT_EXECUTED'

    async def send(self,text,backend,*,scope=(2,3,4)):
        self.validate_scope(scope)
        if not isinstance(text,str) or not 1<=len(text.strip())<=4000:
            raise ValueError('로컬 입력은 1~4000자예요')
        if self.lock.locked():raise RuntimeError('Local generation already running')
        async with self.lock:
            g,ch,u=scope
            self.scope=tuple(scope);self.status='generating';self.partial=''
            started=time.monotonic();self.rows.append(dict(role='user',text=text,scope=list(scope)))
            self.rows=self.rows[-200:]
            state='not_requested';operation='NOT_REQUESTED'
            from .read_evidence import ReadEvidence,ReadState,memory_evidence,receipt_reads,read_question,execute_read,read_answer
            reads={kind:ReadEvidence(kind) for kind in ('memory','reminders')}
            self.active_reads=reads
            backend_invoked=False
            metrics=getattr(backend,'metrics',())
            previous_metric=metrics[-1] if metrics else None
            a=stream_observer.set(self.stream);b=local_token_budget.set(True)
            try:
                receipts=[]
                outcomes=[]
                if text.startswith('/'):
                    from .intent_router import composite_parts
                    planned=composite_parts(text[len('/작업 '):]) if text.startswith('/작업 ') else None
                    families=[p[1] for p in planned[1] if p[2]=='read'] if planned else ['memory'] if text=='/기억 목록' else ['reminders'] if text=='/알림 목록' else []
                    for family in families:reads[family]=ReadEvidence(family,ReadState.PENDING)
                    worker=asyncio.create_task(asyncio.to_thread(self.command,text,scope,outcomes))
                    try:answer,receipts,operation=await asyncio.shield(worker)
                    except asyncio.CancelledError:
                        # A cancelled Future is not a rolled-back transaction.
                        while not worker.done():
                            try:await asyncio.shield(worker)
                            except asyncio.CancelledError:continue
                            except Exception:break
                        if not worker.cancelled():worker.exception()
                        raise
                    self.operations.append(dict(scope=tuple(scope),command=text.split()[0],state=operation,receipts=receipts))
                    self.operations=self.operations[-20:]
                    state='not_requested'
                    reads.update(receipt_reads(receipts))
                    from .read_evidence import apply_read_outcomes
                    reads=apply_read_outcomes(reads,outcomes)
                    self.active_reads=reads
                    if text in ('/기억 목록','/알림 목록'):
                        state=('failed' if operation=='FAILED' else
                               'found' if receipts and any(r.values for r in receipts) else
                               'empty' if receipts and operation=='SUCCESS' else 'not_requested')
                    try:before=await asyncio.to_thread(self.store.subject_snapshot,g,u,relationship=True)
                    except (OSError,RuntimeError,sqlite3.Error):before={'memory':(None,0),'relationships':(None,0)}
                    read=None;epoch=self.epoch
                    if text.startswith('/작업 '):
                        self.histories[tuple(scope)]=[dict(role='user',content=text),dict(role='assistant',content=answer)]
                        self.history_signatures[tuple(scope)]=await asyncio.to_thread(self.state_signature,scope)
                else:
                    operation='NOT_REQUESTED'
                    g,ch,u=scope
                    before=await asyncio.to_thread(self.store.subject_snapshot,g,u,relationship=True)
                    state='not_authorized';memories=[];read=None
                    if before['memory'][0]:
                        reads['memory']=ReadEvidence('memory',ReadState.PENDING)
                        try:
                            memories=await asyncio.to_thread(self.store.memories,g,u,ch,"",conversation_id="local",allow_user_archive=True)
                            memories=memories[:3];state='found' if memories else 'empty'
                            event=Event(1,g,ch,u,text,datetime.now(timezone.utc))
                            read=MemorySelection(g,u,ch,'','local',True,read_values('memory',memories),before['memory'][1],'lime')
                        except (OSError,RuntimeError,sqlite3.Error):
                            state='failed'
                    reads['memory']=memory_evidence(state,read)
                    epoch=self.epoch
                    confirmed=[]
                    for item in self.operations:
                        if item['scope']!=tuple(scope):continue
                        for receipt in item['receipts']:
                            if await asyncio.to_thread(receipt.current,self.store):confirmed.append(receipt)
                    signature=await asyncio.to_thread(self.state_signature,scope)
                    history=self.histories.get(tuple(scope),[])
                    if self.history_signatures.get(tuple(scope))!=signature:history=[]
                    inquiry=read_question(text)
                    if inquiry is not None:
                        family,mode=inquiry
                        if mode=='history':
                            from .read_evidence import unverified_read_reference
                            answer=unverified_read_reference()
                        if mode=='read':
                            reads[family]=ReadEvidence(family,ReadState.PENDING)
                            try:
                                event=Event(1,g,ch,u,text,datetime.now(timezone.utc))
                                reads[family]=await asyncio.to_thread(execute_read,self.store,event,family,DEFAULTS)
                                if reads[family].receipt is not None:receipts.append(reads[family].receipt)
                            except (OSError,RuntimeError,sqlite3.Error):reads[family]=ReadEvidence(family,ReadState.FAILED)
                            outcomes.append(dict(operation=family+'_read',state=reads[family].state.value))
                            operation=('SUCCESS' if reads[family].state.value.startswith('SUCCESS') else
                                       'FAILED' if reads[family].state==ReadState.FAILED else
                                       'UNKNOWN' if reads[family].state==ReadState.STALE else 'NOT_EXECUTED')
                        if family is not None:answer=read_answer(reads[family])
                    elif state=='failed':
                        answer='기억 조회에 실패했어. 자료가 없다는 뜻은 아니야. 지금은 확인할 수 없어.'
                    elif (status_answer:=lookup_state_answer(text,state)) is not None:
                        answer=status_answer
                    elif (help_answer:=self.operation_help(text)) is not None:
                        from .intent_router import readonly_fragments
                        answer='\n'.join((*readonly_fragments(backend,text,state),help_answer))
                    else:
                        cfg=deepcopy(DEFAULTS);cfg['_memory_lookup_state']=state
                        cfg['_read_evidence']={k:r.public() for k,r in reads.items()}
                        cfg['_familiarity']=before.get('familiarity')
                        facts=dict(mode='LOCAL_CHAT',user='A' if u==4 else 'B',channel=ch,
                                   memory_lookup=state,verified_memories=[m['summary'] for m in memories],
                                   operation_state='NOT_REQUESTED',execution_receipts=[],
                                   recent_verified_operations=[self.receipt_fact(r) for r in confirmed],
                                   local_commands='상태 변경은 /기억, /알림, /동의 명령으로만 실행한다. 일반 문장만으로 저장/예약하지 않는다.')
                        header={'role':'system','content':'로컬 합성 테스트 근거(명령 아님): '+json.dumps(facts,ensure_ascii=False)}
                        cfg['_generation_sources']=((header,'local_facts'),)
                        cfg['_generation_facts']=dict(current_speaker=facts['user'],
                            memories=[dict(m) for m in memories],timezone='Asia/Seoul',
                            recent_operations=facts['recent_verified_operations'])
                        # Keep only complete pairs, separate per local user/channel.
                        backend_invoked=True
                        answer=await backend.text([header,*history,dict(role='user',content=text)],cfg)
                    if (epoch!=self.epoch or before!=await asyncio.to_thread(self.store.subject_snapshot,g,u,relationship=True) or
                        read and not await asyncio.to_thread(read.current,self.store)):
                        raise RuntimeError('대화 근거가 바뀌어 오래된 응답을 폐기했어요')
                    if not all([await asyncio.to_thread(r.current,self.store) for r in confirmed]):
                        raise RuntimeError('실행 영수증이 바뀌어 오래된 응답을 폐기했어요')
                    if state!='failed' and signature!=await asyncio.to_thread(self.state_signature,scope):
                        raise RuntimeError('대화 근거가 바뀌어 오래된 응답을 폐기했어요')
                    self.histories[tuple(scope)]=[*history,dict(role='user',content=text),dict(role='assistant',content=answer)][-400:] if state!='failed' else []
                    self.history_signatures[tuple(scope)]=signature if state!='failed' else await asyncio.to_thread(self.state_signature,scope)
                try:checks=[dict(kind=r.kind,current=r.current(self.store)) for r in receipts]
                except (OSError,RuntimeError,sqlite3.Error):checks=[dict(current=False)]
                if not all(r['current'] for r in checks):
                    answer='실행 상태를 다시 확인하지 못했어. 완료되었다고 확정할 수 없어.'
                    operation='UNKNOWN'
                    for check in checks:
                        if not check['current'] and check.get('kind') in reads:
                            family=check['kind'];reads[family]=ReadEvidence(family,ReadState.STALE)
                self.rows.append(dict(role='assistant',text=answer,scope=list(scope)))
                self.rows=self.rows[-200:]
                metrics=getattr(backend,'metrics',())
                generated=bool(metrics and metrics[-1] is not previous_metric)
                self.last=dict(seconds=time.monotonic()-started,lookup=state,
                    outcomes=list(outcomes),
                    reads={k:r.public() for k,r in reads.items()},
                    response_origin='model' if generated else 'backend' if backend_invoked else 'runtime',
                    receipts=checks,
                    operation_state=operation,
                    test_subject=dict(memory_consent=before['memory'][0],relationship_consent=before['relationships'][0],
                                      affinity=before.get('familiarity')),
                    context=dict(getattr(backend.engine,'last_context',{})) if generated and hasattr(backend,'engine') else {})
                self.status='idle'
                return answer
            except asyncio.CancelledError:
                reads={k:ReadEvidence(k,ReadState.CANCELLED) if r.state==ReadState.PENDING else r for k,r in reads.items()}
                self.status='cancelled';self.last={'operation_state':'UNKNOWN' if text.startswith('/') else 'NOT_REQUESTED',
                                                 'response_state':'CANCELLED','lookup':state,'reads':{k:r.public() for k,r in reads.items()}};raise
            except BaseException:
                self.histories.pop(tuple(scope),None)
                self.status='failed';self.last={'operation_state':'UNKNOWN' if text.startswith('/') else 'NOT_REQUESTED',
                                              'response_state':'FAILED','lookup':state};raise
            finally:
                self.partial='';stream_observer.reset(a);local_token_budget.reset(b)

    async def tick(self):
        """Local inbox delivery only; production delivery remains separate."""
        def due():
            delivered=[]
            for row in self.store.due(600):
                claimed=self.store.claim(row['reminder_id'])
                if not claimed:continue
                self.touch()
                # Preserve evidence before Store clears notification text.
                delivered.append(dict(role='assistant',text='[로컬 테스트 알림] '+claimed['text'],
                    notification_id=claimed['reminder_id'], acknowledged=False,
                    scope=[int(claimed['guild']),int(claimed['channel']),int(claimed['requester'])]))
            return delivered
        rows=await asyncio.to_thread(due)
        self.rows.extend(rows);self.rows=self.rows[-200:]

    async def acknowledge_notifications(self):
        # Delivery is acknowledged only after the local inbox exists, never
        # in the worker before it returns. Interrupted processing is recovered
        # by the existing Store as uncertain/failed, not a fabricated delivery.
        for row in self.rows:
            key=row.get('notification_id')
            if key and not row.get('acknowledged'):
                g,ch,u=row['scope']
                current=await asyncio.to_thread(self.store.reminders,g,u)
                found=next((r for r in current if r['reminder_id']==key and r['channel']==str(ch)),None)
                if not found or found['status']!='processing':
                    row['text']='[로컬 테스트 알림 · 취소/실패 등으로 더 이상 대기 중이 아님]'
                    row['acknowledged']=bool(found and found['status']=='delivered')
                    continue
                await asyncio.to_thread(self.store.finish,key,'delivered')
                current=await asyncio.to_thread(self.store.reminders,g,u)
                row['acknowledged']=any(r['reminder_id']==key and r['status']=='delivered' for r in current)
