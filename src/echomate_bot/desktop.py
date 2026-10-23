"""Native local owner console. Tk stays on main thread, Discord/GPU on workers.

The signed bootstrap and its Windows ACL are the local authorization boundary.
This does not expose an HTTP server or accept remote GUI control requests.
"""
from __future__ import annotations
import asyncio
import json
import logging
import queue
import sqlite3
from contextlib import closing
import threading
import time
from pathlib import Path
import tkinter as tk

from .settings import ROOT,Settings,MOODS,ACTIVITY

STAGES={'utterance_wait':'메시지 보충 대기','social':'실제 청자·대화 흐름 판정','member_resolution':'호칭·답장 근거 확인','summary':'대화 요약 확인·압축', 'conversation_wait':'앞선 질문을 처리하는 중','memory_lookup':'필요한 기억 확인','private_request':'기억·예약 요청 처리','assessment':'참여·대화 지속 판단','continuity':'대화 지속 판단','visual':'이미지 분석',
        'action':'행동 선택','text':'답변 작성','sending':'Discord 전송','research':'인터넷 원문·근거 확인','output_check':'출력 정책 검사'}
NO_RESPONSE = {
    'utterance_waiting':'호출·연속 발언의 보충을 잠시 기다려요', 'utterance_combined':'같은 작성자의 이어지는 조각을 결합했어요',
    'legacy_command_unregistered':'이전 명령이에요. /동의로 본인 데이터 설정을 열어 주세요',
    'capability_state_changed':'설명 도중 기능·동의 상태가 바뀌어 오래된 안내를 보내지 않았어요',
    'visual_asset_unavailable':'이미지 분석을 완료하지 못해 내용을 추측하지 않았어요',
    'attention_followup_linked':'확인된 단독 호출 뒤의 첫 발언을 연결했어요',
    'utterance_separated':'독립 발언 또는 출처 경계로 나눴어요', 'utterance_invalidated':'원본 변경이나 접근 범위 변경으로 발언을 중단했어요',
    'resource_stop_commit':'Windows 가상 메모리 여유가 부족해요. 다른 작업을 마친 뒤 다시 준비해 주세요',
    'social_human_exchange_pending':'다른 사람과 주고받는 순서라 끼어들지 않았어요', 'social_candidate_capacity':'여러 대화의 연결이 불명확해 기다려요',
    'social_other_addressee':'다른 사람에게 한 말이라 참여하지 않았어요', 'social_broadcast':'채널 전체를 향한 말이라 먼저 답하지 않았어요',
    'social_uncertain':'누구에게 한 말인지 확실하지 않아 기다려요', 'social_join_not_invited':'봇에게 합류를 요청한 근거가 부족해요',
    'social_group_not_invited':'봇이 포함된 그룹 초대가 확인되지 않았어요', 'social_no_response_expected':'봇의 답을 기대하는 발언이 아니에요',
    'social_addressee_shift':'대화 상대가 다른 사람으로 바뀌었어요', 'social_invalid_anchor':'연결할 대화의 근거를 확인하지 못했어요',
    'resource_stop_temperature':'GPU 온도 보호로 멈췄어요', 'resource_stop_vram':'GPU 메모리 여유가 부족해 멈췄어요', 'resource_stop_ram':'PC 메모리 여유가 부족해 멈췄어요', 'resource_stop_gpu_query':'GPU 상태를 확인할 수 없어 멈췄어요',
    'name_not_recognized':'등록된 호출 형태가 없어요', 'name_ambiguous':'이름은 보이지만 부른 대상이 불분명해요',
    'followup_not_linked':'이어지는 대화 근거가 부족해요', 'continuation_rejected':'대상이나 종료 판단에 따라 답하지 않았어요',
    'autonomy_cooldown':'새 자율 참여의 대기 시간 또는 부하 제한이에요', 'scope_denied':'허용된 대화 범위가 아니에요',
    'permission_denied':'채널을 볼 권한이 없어요',
    'duplicate_request':'이미 처리한 요청이에요', 'response_cooldown':'발언 간격을 기다리고 있어요',
    'reaction_disabled':'이 범위의 이모지 반응이 꺼져 있어요',
    'member_other_addressee':'다른 구성원에게 한 말로 확인했어요',
    'queue_rejected':'작업 대기 한도에 도달했어요', 'request_expired':'요청의 최대 대기 시간이 지났어요',
    'conversation_capacity_veto':'동시에 처리 중인 대화가 많아 새 요청을 받지 못했어요',
    'stale_context':'생성 중 대화나 설정이 바뀌었어요', 'generation_failed':'AI 처리 중 오류가 났어요',
    'action_silence':'현재 문맥에서는 침묵을 선택했어요', 'send_failed':'Discord 전송을 확인하지 못했어요',
}

MODES={'침묵':'silent','멘션·대화 이어가기':'mention','문맥에 따라 자율 참여':'autonomous'}
ACTIVITIES={'조용함':'quiet','보통':'normal','활발함':'active','매우 활발함':'very_active'}


class LocalController:
    """Every settings mutation and client access runs on the same event loop."""
    def __init__(self):
        self.updates=queue.Queue(maxsize=8);self.loop=None;self.client=None;self.job=None
        self.phase='설정 읽는 중';self.error='';self.lease=None
        self.inventory=[];self.closed=threading.Event()
        self.thread=threading.Thread(target=self._thread,name='echomate-discord',daemon=True)
        self.thread.start()

    def _thread(self):
        try:asyncio.run(self._main())
        except asyncio.CancelledError:pass
        finally:
            if self.lease:self.lease.close()
            self.closed.set()

    async def _main(self):
        self.loop=asyncio.get_running_loop();self.main_task=asyncio.current_task()
        try:
            from .instance import InstanceLease
            self.lease=InstanceLease()
            from .onboarding import load_bootstrap
            self.bootstrap=load_bootstrap(ROOT/'bootstrap.json')
            self.settings=Settings(self.bootstrap['owner_id'],self.bootstrap['signing_key'],ROOT/'settings.json')
            from .character_profiles import ProfileStore
            self.profiles_view=ProfileStore(ROOT/'characters.json',self.bootstrap['owner_id'],self.bootstrap['signing_key']).list()
            from .companion_store import CompanionStore
            self.companion=CompanionStore(ROOT/'companion.sqlite3');self.companion_view={}
            self.record_guilds=await asyncio.to_thread(self.companion.guild_ids) if not self.companion.error else []
            cached=ROOT/'inventory.json'
            if cached.exists():
                try:self.inventory=json.loads(cached.read_text(encoding='utf-8'))
                except (OSError,ValueError):self.error='저장된 서버 목록을 읽지 못했어요'
            self.phase='서버와 채널 목록을 불러오고 있어요'
            self._publish()
            # Local records remain available without logging into Discord.
            if not self.job or self.job.done():self.phase='정지 — 시작 버튼으로 연결'
        except Exception as exc:
            self.phase='다른 EchoMate 앱이 실행 중이야' if isinstance(exc,RuntimeError) else '처음 사용 안내에서 봇 정보를 등록해 주세요'
            self.error=type(exc).__name__
            self.settings=None
        from .model_registry import ModelRegistry
        self.models=await asyncio.to_thread(ModelRegistry(self.settings.get()['model_roots'] or None if self.settings else None).scan)
        while True:
            self._publish()
            await asyncio.sleep(.4)

    def _publish(self):
        cfg=self.settings.get() if self.settings else None
        client=self.client
        servers=[]
        if cfg:
            guild_ids=set(self.bootstrap['admin_guilds'])
            guild_ids.update(map(int,cfg['guilds']))
            guild_ids.update(getattr(self,'record_guilds',[]))
            guild_ids.update(g['id'] for g in getattr(self,'inventory',[]))
            if client and client.is_ready():guild_ids.update(g.id for g in client.guilds)
            for gid in sorted(guild_ids):
                guild=client.get_guild(gid) if client and client.is_ready() else None
                g=cfg['guilds'].get(str(gid),dict(enabled=False,channels={},threads={}))
                saved=next((g for g in getattr(self,'inventory',[]) if g['id']==gid),None)
                channels={c['id']:c for c in saved['channels']} if saved else {}
                if guild:
                    import discord
                    for c in [*guild.channels,*guild.threads]:
                        if isinstance(c,(discord.TextChannel,discord.ForumChannel,discord.Thread)):
                            label=(c.parent.name+' / ' if isinstance(c,discord.Thread) and c.parent else '')+c.name
                            channels[c.id]=dict(id=c.id,label=label,thread=isinstance(c,discord.Thread),parent=c.parent_id if isinstance(c,discord.Thread) else None)
                for table in ('channels','threads'):
                    for cid in g[table]:channels.setdefault(int(cid),dict(id=int(cid),label='등록된 '+('스레드' if table=='threads' else '채널'),thread=table=='threads'))
                servers.append(dict(id=gid,label=guild.name if guild else saved['label'] if saved else f'서버 {gid} · 로컬 자료',enabled=g['enabled'],channels=list(channels.values()),
                    joined=bool(guild) if client and client.is_ready() else bool(saved)))
        runtime=client.runtime if client else None
        progress=[]
        if runtime:
            for cid,p in list(runtime.progress.items()):
                channel=client.get_channel(p.get('channel',cid))
                progress.append(dict(channel=channel.name if channel else '허용된 채널',stage=STAGES.get(p['stage'],p['stage']),seconds=round(time.time()-p['started'],1)))
        preview=getattr(self,'preview_task',None);preview_busy=bool(preview and not preview.done())
        serving=client.backend if client else getattr(self,'preview_backend',None)
        preparing=bool(getattr(self,'starting_model',False) or getattr(self,'model_preparing',False) or runtime and getattr(runtime,'changing_model',False) or preview_busy and getattr(serving,'model',None) is None)
        try:
            from .ledger import Ledger
            statistics=runtime.ledger.statistics() if runtime else Ledger.read_statistics(self.settings.path.parent/'sent.sqlite3') if cfg else {}
        except (OSError,sqlite3.Error):statistics=dict(error=True);self.error='전송 통계를 읽지 못했어요'
        if preview_busy:progress.append(dict(channel='로컬 미리보기',stage='취소·GPU 정리' if getattr(self,'preview_cancelling',False) else '모델 준비' if preparing else 'GPU 작업 대기·처리',seconds=round(time.monotonic()-getattr(self,'preview_started',time.monotonic()),1)))
        snapshot=dict(phase='AI 안전 보호로 정지 · 진단 확인 후 다시 시작' if runtime and runtime.stopped and getattr(client.backend,'failed',False) else '미리보기 취소 중 · GPU 작업을 정리하고 있어요' if getattr(self,'preview_cancelling',False) else '로컬 미리보기 · 모델 준비 중' if preview_busy and preparing else '로컬 미리보기 · GPU 작업 대기·처리 중' if preview_busy else '모델을 준비하고 있어요 · 완료 전에는 답하지 않아요' if preparing else self.phase,error=self.error,notice=getattr(self,'notice',''),cfg=cfg,servers=servers,progress=progress,
                      model_preparing=preparing,
                      model_load_phase={'registry_preflight':'모델 파일·메모리 여유 확인','framework_imports':'추론 엔진 준비',
                          'processor':'토크나이저·입력 처리 준비','model_init_weights_nf4':'가중치 읽기·GPU 이동·NF4 변환',
                          'loaded':'가중치 로딩 완료 · 시험 추론 확인','released':'모델 해제 완료','failed':'모델 준비 실패'}.get(getattr(serving,'load_phase',None),''),
                      preview_busy=preview_busy,preview_session=getattr(self,'preview_session',None),
                      preview_cleanup_failed=getattr(self,'preview_cleanup_failed',False),
                      preview_rejection=getattr(self,'preview_rejection',{}),
                      last_management_error=getattr(self,'last_management_error',{}),
                      model_load_seconds=getattr(serving,'load_seconds',None),
                      model_switch_seconds=getattr(client.backend,'switch_seconds',None) if client else None,
                      models=[m.public() for m in getattr(self,'models',[])],profiles=getattr(self,'profiles_view',{}),preview=getattr(self,'preview_result',''),
                      recent_reason=next((NO_RESPONSE.get(r['code'],'') for r in reversed(runtime.diagnostics) if r['code'] in NO_RESPONSE or r['code']=='response_sent'),'') if runtime else '',
                      scheduler=serving.scheduler.snapshot() if serving and hasattr(serving,'scheduler') else {},
                      command_review=getattr(self,'command_review',None),
                      command_status=getattr(client,'command_status',{}) if client else {},
                      companion=getattr(self,'companion_view',{}),companion_error=getattr(getattr(self,'companion',None),'error',None),
                      companion_loading=getattr(self,'companion_loading',False),
                      statistics=statistics,
                      runtime_totals=dict(runtime.totals) if runtime else {},
                      conversations=runtime.social_monitor() if runtime and hasattr(runtime,'social_monitor') else [],
                      jobs=runtime.monitor() if runtime and hasattr(runtime,'monitor') else getattr(self,'last_jobs',[]),
                      memory_pending=runtime.memory_queue.qsize() if runtime else 0,
                      private_service=bool(runtime and runtime.service_task and not runtime.service_task.done()),
                      running=bool(self.job and not self.job.done()),
                      connected=bool(client and client.is_ready()),pending=(len(runtime.tasks.keys()|runtime.deferred_events.keys()) if runtime else 0)+int(preview_busy),
                      contexts=runtime.activity_changed() if runtime else 0,safe_stopped=runtime.stopped if runtime else False,
                      latency=runtime.latencies[-1] if runtime and runtime.latencies else None,
                      gpu_seconds=client.backend.metrics[-1]['seconds'] if client and client.backend.metrics else None)
        if self.updates.full():
            try:self.updates.get_nowait()
            except queue.Empty:pass
        if snapshot['preview_cleanup_failed']:snapshot['phase']='미리보기 정리 실패 · 앱을 닫고 다시 열어 주세요'
        self.updates.put_nowait(snapshot)
        if getattr(self,'lease',None) and time.monotonic()-getattr(self,'_published_at',0)>2:
            from .settings import atomic_private_json
            try:
                atomic_private_json(ROOT/'desktop-status.json',dict(updated=time.time(),phase=self.phase,error=self.error,
                    connected=snapshot['connected'],pending=snapshot['pending'],safe_stopped=snapshot['safe_stopped'],
                    stages=[dict(stage=p['stage'],seconds=p['seconds']) for p in progress],latencies=runtime.latencies if runtime else []))
            except OSError:self.error='StatusWriteError'
            self._published_at=time.monotonic()

    def submit(self,operation,**kwargs):
        if self.loop and not self.loop.is_closed() and not self.closed.is_set():
            future=asyncio.run_coroutine_threadsafe(self.command(operation,**kwargs),self.loop)
        else:
            from concurrent.futures import Future
            future=Future();future.set_result(dict(ok=False,error='앱이 아직 준비되지 않았거나 종료 중이에요. 잠시 뒤 다시 시도해 주세요.'))
        self.last_submission=future
        return future

    def known_guild(self,gid):
        return gid in self.bootstrap['admin_guilds'] or gid in getattr(self,'record_guilds',[]) or any(g['id']==gid for g in getattr(self,'inventory',[])) or bool(self.client and self.client.is_ready() and self.client.get_guild(gid))

    async def refresh_inventory(self):
        """Metadata-only REST, available without loading the model or sending messages."""
        if getattr(self,'refreshing',False):return
        self.refreshing=True
        import discord
        logging.getLogger('discord').setLevel(logging.CRITICAL)
        reader=discord.Client(intents=discord.Intents.none())
        try:
            await reader.login(self.bootstrap['token'])
            inventory=[]
            async for guild in reader.fetch_guilds(limit=200):
                channels=await guild.fetch_channels();parents={c.id:c.name for c in channels}
                entries=[dict(id=c.id,label=c.name,thread=False) for c in channels if isinstance(c,(discord.TextChannel,discord.ForumChannel))]
                entries.extend(dict(id=t.id,label=parents.get(t.parent_id,'')+' / '+t.name,thread=True,parent=t.parent_id) for t in await guild.active_threads())
                inventory.append(dict(id=guild.id,label=guild.name,channels=entries))
            self.inventory=inventory
            from .settings import atomic_private_json
            atomic_private_json(ROOT/'inventory.json',inventory)
        except Exception as exc:self.error='목록 갱신 실패 · '+type(exc).__name__
        finally:
            await reader.close();self.refreshing=False

    async def _cancel_preview(self):
        task=getattr(self,'preview_task',None)
        if task is None:return
        backend=getattr(self,'preview_backend',None);owned=getattr(self,'preview_owned',False)
        self.preview_cancelling=not task.done();self._publish()
        try:
            task.cancel();await asyncio.gather(task,return_exceptions=True)
            # A task cancelled before its coroutine first runs cannot execute
            # its finally block. The controller still owns that backend.
            if backend is not None and getattr(self,'preview_backend',None) is backend and not getattr(self,'preview_cleanup_failed',False):
                try:
                    if owned:await backend.close()
                except Exception:
                    self.preview_cleanup_failed=True;raise
                else:self.preview_backend=None
            if task.cancelled():self.preview_result='미리보기를 취소했어요'
        finally:self.preview_cancelling=False

    async def command(self,operation,**kwargs):
        if operation in {'start','stop','shutdown','name','preview','preview_cancel','setup','models','profiles'} or (operation=='settings' and 'model' in kwargs.get('values',{})):
            if not hasattr(self,'lifecycle_lock'):self.lifecycle_lock=asyncio.Lock()
            async with self.lifecycle_lock:return await self._command(operation,**kwargs)
        return await self._command(operation,**kwargs)

    async def _command(self,operation,**kwargs):
        success=True
        try:
            if operation=='shutdown':
                try:await self._cancel_preview()
                except Exception as exc:self.error='PreviewCleanup'+type(exc).__name__
                if getattr(self,'settings',None):
                    try:self.settings.set(self.bootstrap['owner_id'],'enabled',False)
                    except OSError:self.error='SettingsWriteError'
                if self.job and not self.job.done():
                    self.job.cancel();await asyncio.gather(self.job,return_exceptions=True)
                self.main_task.cancel();return
            if operation=='setup':
                if self.settings or (ROOT/'bootstrap.json').exists():raise PermissionError('Existing setup preserved')
                if not self.lease:raise PermissionError('Another app owns setup')
                from .onboarding import create_installation
                self.bootstrap=await asyncio.to_thread(create_installation,ROOT/'bootstrap.json',int(kwargs['owner']),kwargs['token'])
                self.settings=Settings(self.bootstrap['owner_id'],self.bootstrap['signing_key'],ROOT/'settings.json')
                from .companion_store import CompanionStore
                self.companion=CompanionStore(ROOT/'companion.sqlite3');self.companion_view={};self.record_guilds=[]
                self.phase='등록 완료 · AI 모델과 허용 채널을 선택해 주세요';self._publish();return dict(ok=True,error='')
            if not self.settings:raise ValueError('Setup required')
            owner=self.bootstrap['owner_id'];self.settings.authorize(owner)
            self.error=''
            if getattr(self,'preview_cleanup_failed',False) and (operation in ('start','preview','models') or operation=='settings' and 'model' in kwargs.get('values',{})):
                raise RuntimeError('미리보기 정리에 실패했어요. 앱을 닫고 다시 열어 주세요.')
            if getattr(self,'starting_model',False) and (operation=='models' and 'roots' in kwargs or operation=='settings' and 'model' in kwargs.get('values',{})):
                raise ValueError('최초 모델 준비가 끝난 뒤 변경해 주세요')
            preview=getattr(self,'preview_task',None)
            if operation=='stop' and preview and not preview.done():
                await self._cancel_preview()
            if preview and not preview.done() and (operation in ('start','stop','preview') or operation=='settings' and 'model' in kwargs.get('values',{})):
                raise ValueError('미리보기가 끝난 뒤 모델을 변경하거나 시작해 주세요')
            if operation=='models':
                from .model_registry import ModelRegistry
                roots=kwargs.get('roots',self.settings.get()['model_roots'])
                active=self.settings.get()['model']
                previous=next((m.path for m in getattr(self,'models',[]) if m.id==active and m.compatible),None)
                if previous and previous not in roots and 'roots' in kwargs:roots=[*roots,previous]
                from .settings import validate
                validate(dict(self.settings.get(),model_roots=roots))
                self.models=await asyncio.to_thread(ModelRegistry(roots or None).scan)
                self.settings.set(owner,'model_roots',roots)
                if self.client:self.client.backend.model_roots=roots or None
                self.notice='모델 목록을 다시 확인했어요'
            elif operation=='profiles':
                from .character_profiles import ProfileStore,DEFAULT_PROFILE
                store=ProfileStore(self.settings.path.parent/'characters.json',owner,self.bootstrap['signing_key']);action=kwargs.get('action','list');key=kwargs.get('key','default')
                if action in ('save','save_apply'):
                    await asyncio.to_thread(store.save,owner,key,kwargs['value'])
                    if action=='save_apply':
                        from .character_profiles import SHARED_FIELDS
                        profile=(await asyncio.to_thread(store.list))[key]
                        self.settings.change(owner,lambda cfg:cfg.update(character_profile=profile,**{k:profile[k] for k in SHARED_FIELDS}))
                elif action=='delete':await asyncio.to_thread(store.save,owner,key)
                elif action=='import':await asyncio.to_thread(store.import_file,owner,key,kwargs['path'])
                elif action=='export':await asyncio.to_thread(store.export_file,key,kwargs['path'])
                elif action=='export_current':await asyncio.to_thread(store.export_value,self.settings.get()['character_profile'],kwargs['path'])
                elif action in ('apply','restore'):
                    from .character_profiles import SHARED_FIELDS
                    profile=store.list()[key] if action=='apply' else dict(DEFAULT_PROFILE)
                    self.settings.change(owner,lambda cfg:cfg.update(character_profile=profile,**{k:profile[k] for k in SHARED_FIELDS}))
                self.profiles_view=await asyncio.to_thread(store.list)
                self.notice='캐릭터 설정을 확인했어요'
            elif operation=='preview_cancel':
                if kwargs.get('session') and kwargs['session']==getattr(self,'preview_session',None) and preview and not preview.done():
                    await self._cancel_preview()
            elif operation=='preview':
                text=kwargs['text']
                if not isinstance(text,str) or not 1<=len(text)<=1000:raise ValueError('Invalid preview input')
                self.preview_rejection={};self.preview_result='로컬에서 답변을 준비하고 있어요';self._publish()
                from .inference import LocalBackend
                from .character_profiles import validate_profile,applied_profile,presets,SHARED_FIELDS
                from .character import effective_character
                from copy import deepcopy
                cfg=self.settings.get();variants=[]
                if kwargs.get('compare'):selected=[('프리셋',dict(p,**{k:cfg[k] for k in ('mood','gender','activity')})) for p in presets().values()]
                elif kwargs.get('profile') is not None:selected=[('저장본 · 미적용' if kwargs.get('profile_source')=='saved' else '미적용 편집본',deepcopy(validate_profile(kwargs['profile'])))]
                else:selected=[('현재 적용',applied_profile(cfg))]
                for label,p in selected:
                    variant=deepcopy(cfg);variant.update(character_profile=deepcopy(p),**{k:p[k] for k in SHARED_FIELDS});variant['_familiarity']=None
                    variants.append((label,p['name'],effective_character(variant,text)))
                backend=self.client.backend if self.client else LocalBackend(model_id=cfg['model'],model_roots=cfg['model_roots'] or None)
                owns_backend=self.client is None
                self.preview_session=kwargs.get('session');self.preview_backend=backend;self.preview_owned=owns_backend;self.preview_started=time.monotonic()
                async def generate_preview():
                    try:
                        results=[]
                        for label,name,variant in variants:
                            results.append('['+label+' · '+name+' · '+variant['mood']+']\n'+await backend.text([dict(role='user',content=text)],variant))
                            self.preview_result='\n\n'.join(results);self._publish()
                    except asyncio.CancelledError:self.preview_result='미리보기를 취소했어요';raise
                    except Exception as exc:
                        from .processes import ResourceLimitError,resource_message
                        self.preview_result='미리보기 실패 · '+(resource_message(exc,'모델 준비 자원이 부족해요') if isinstance(exc,ResourceLimitError) else type(exc).__name__)
                    finally:
                        try:
                            if owns_backend:await backend.close()
                        except Exception:
                            self.preview_cleanup_failed=True;raise
                        else:self.preview_backend=None
                self.preview_task=asyncio.create_task(generate_preview())
                def completed(task):
                    if not task.cancelled() and task.exception():
                        self.error=('PreviewCleanup' if getattr(self,'preview_cleanup_failed',False) else 'Preview')+type(task.exception()).__name__
                        self.last_management_error=dict(operation='preview',kind=type(task.exception()).__name__,message=self.error,at=time.time())
                    self._publish()
                self.preview_task.add_done_callback(completed)
                # No Runtime ingestion: consent, memory, affinity and reminders untouched.
            elif operation in ('command_review','command_apply'):
                if not self.client or not self.client.is_ready():raise ValueError('봇 연결 후 명령 목록을 확인해 주세요')
                if operation=='command_review':
                    self.command_review=None;self.notice='명령 목록 조회 중 · 변경하지 않아요';self._publish()
                    client=self.client;plan=await client.review_commands(owner)
                    if self.client is not client:raise ValueError('Application connection changed')
                    self.command_review=plan;self.notice='명령 목록 조회 완료 · 변경은 별도 승인 후에만 실행해요'
                else:
                    await self.client.apply_commands(owner,kwargs['fingerprint']);self.command_review=None;self.notice='API 등록 확인 완료 · Discord 화면 표시와 실행은 별도 확인이 필요해요'
            elif operation=='refresh':await self.refresh_inventory()
            elif operation=='start':
                self.settings.set(owner,'enabled',True)
                if self.job and not self.job.done():return dict(ok=True,error='')
                self.job=asyncio.create_task(self._run_bot())
            elif operation=='stop':
                self.settings.set(owner,'enabled',False)
                self.phase='종료·GPU 정리 중'
                if self.job and not self.job.done():
                    self.job.cancel()
                    await asyncio.gather(self.job,return_exceptions=True)
                self.phase='정지'
            elif operation=='settings':
                values=kwargs['values']
                if 'expected_profile' in kwargs:
                    from .character_profiles import applied_profile
                    if applied_profile(self.settings.get())!=kwargs['expected_profile']:raise ValueError('Character changed; reopen editor')
                allowed={'enabled','text','reactions','vision','mood','gender','warmth','cuteness','playfulness','activity','cooldown','engagement_seconds','model','adult_humor','character_profile','memory_auto','relations_auto','context_excerpts','reminders_enabled','reminder_grace','memory_plan_grace','memory_date_grace','memory_state_hours','command_sync_pending','web_search','summaries_auto'}
                if set(values)-allowed:raise ValueError('Unknown GUI setting')
                from .settings import validate
                from .character_profiles import SHARED_FIELDS
                if 'character_profile' in values:
                    values=dict(values,**{k:values['character_profile'][k] for k in SHARED_FIELDS})
                elif set(values)&set(SHARED_FIELDS) and self.settings.get()['character_profile']:
                    values=dict(values,character_profile=dict(self.settings.get()['character_profile'],**{k:v for k,v in values.items() if k in SHARED_FIELDS}))
                validate(dict(self.settings.get(),**values))
                if 'model' in values and self.client:
                    await self.client.runtime.switch_model(owner,values['model'])
                    values={k:v for k,v in values.items() if k!='model'}
                elif 'model' in values:
                    from .inference import LocalBackend
                    cfg=self.settings.get();backend=LocalBackend(model_id=values['model'],model_roots=cfg['model_roots'] or None)
                    self.model_preparing=True;self._publish()
                    try:await backend.prepare_mode(values['model'])
                    finally:
                        try:await backend.close()
                        finally:self.model_preparing=False
                if values:self.settings.change(owner,lambda cfg:cfg.update(values))
                if self.client and values:
                    self.client.runtime.cancel_pending()
            elif operation=='name':
                from .naming import validate_name
                gid=kwargs['guild'];name=validate_name(kwargs['name'])
                if not self.known_guild(gid):raise PermissionError('Guild is not connected')
                def rename(cfg):
                    g=cfg['guilds'].setdefault(str(gid),dict(enabled=False,channels={},threads={}))
                    g['name']=name
                self.settings.change(owner,rename)
                self.notice='이 서버의 봇 이름을 저장했어요'
                if self.client:
                    self.client.runtime.invalidate_all()
                    await self.client.apply_guild_name(gid)
            elif operation=='companion':
                gid=int(kwargs['guild']);action=kwargs['action']
                if not self.known_guild(gid) and str(gid) not in self.settings.get()['guilds']:raise PermissionError('Unknown guild')
                store=self.companion;user=int(kwargs['user']) if kwargs.get('user') else None
                if action=='server_options':
                    from .temporal import zone
                    from .naming import validate_name
                    tz=kwargs['timezone'];zone(tz)
                    aliases=[validate_name(x.strip()) for x in kwargs['aliases'].split(',') if x.strip()]
                    def options(cfg):
                        g=cfg['guilds'].setdefault(str(gid),dict(enabled=False,channels={},threads={}))
                        g.update(timezone=tz,aliases=aliases,partial_names=kwargs['partial_names'])
                    self.settings.change(owner,options)
                    if self.client:self.client.runtime.cancel_pending()
                elif action=='affinity':
                    if not user:raise ValueError('Choose user')
                    if not await asyncio.to_thread(store.automatic_allowed,gid,user,'relationships'):raise ValueError('본인의 친밀도 저장 동의가 필요해요')
                    await asyncio.to_thread(store.set_affinity,gid,user,float(kwargs['value']),require_consent=True)
                elif action=='member_alias':
                    if not user:raise ValueError('Choose user')
                    if kwargs['status']!='deleted' and not await asyncio.to_thread(store.automatic_allowed,gid,user,'relationships'):raise ValueError('본인의 친밀도 저장 동의가 필요해요')
                    channel=int(kwargs['channel']);g=self.settings.get()['guilds'].get(str(gid),{})
                    if str(channel) not in g.get('channels',{}) and str(channel) not in g.get('threads',{}):raise ValueError('Choose configured source channel')
                    await asyncio.to_thread(store.set_alias,gid,channel,user,kwargs['alias'],kwargs['status'],require_consent=True)
                    if self.client:self.client.runtime.members.alias_cache.clear()
                elif action=='forget_user':
                    if not user:raise ValueError('Choose user')
                    await asyncio.to_thread(store.forget,gid,user)
                    if self.client:self.client.runtime.members.clear(gid,user=user)
                elif action=='forget_guild':
                    await asyncio.to_thread(store.forget,gid)
                    if self.client:self.client.runtime.members.clear(gid)
                elif action in ('memory_reset','relationship_reset','reminder_reset'):
                    area={'memory_reset':'memories','relationship_reset':'relationships','reminder_reset':'reminders'}[action]
                    await asyncio.to_thread(store.clear_records,gid,area,user)
                elif action in ('memory_add','memory_edit'):
                    from .temporal import editor_timestamp
                    tz=self.settings.get()['guilds'].get(str(gid),{}).get('timezone','Asia/Seoul')
                    expires=editor_timestamp(kwargs.get('expires',''),tz)
                    if action=='memory_add':
                        if not user:raise ValueError('Choose user')
                        if not await asyncio.to_thread(store.automatic_allowed,gid,user,'memory'):raise ValueError('본인의 기억 저장 동의가 필요해요')
                        channel=int(kwargs['channel'])
                        g=self.settings.get()['guilds'].get(str(gid),{})
                        if str(channel) not in g.get('channels',{}) and str(channel) not in g.get('threads',{}):raise ValueError('Choose configured source channel')
                        key=await asyncio.to_thread(store.add_memory,gid,user,channel,kwargs['summary'],kwargs.get('kind','explicit'),tz=tz,expires=expires,policy=self.settings.get(),require_consent=True)
                        if key is None:raise ValueError('Subject opted out or source deleted')
                    else:await asyncio.to_thread(store.edit_memory,gid,kwargs['key'],kwargs['summary'],expires,kwargs.get('status','active'))
                elif action=='memory_delete':await asyncio.to_thread(store.delete_memory,gid,kwargs['key'])
                elif action=='summary_delete':
                    await asyncio.to_thread(store.delete_digest,gid,kwargs['key'])
                    if self.client:
                        for task in self.client.runtime.summary_tasks:task.cancel()
                elif action=='summary_reset':
                    await asyncio.to_thread(store.clear_digests,gid,user)
                    if self.client:
                        for task in self.client.runtime.summary_tasks:task.cancel()
                elif action in ('reminder_cancel','reminder_edit'):
                    from .temporal import editor_timestamp
                    tz=self.settings.get()['guilds'].get(str(gid),{}).get('timezone','Asia/Seoul')
                    due=editor_timestamp(kwargs.get('due',''),tz) if action=='reminder_edit' else None
                    if action=='reminder_edit' and due is None:raise ValueError('Date required')
                    await asyncio.to_thread(store.change_reminder,gid,owner,kwargs['key'],due=due,text=kwargs.get('text'),cancel=action=='reminder_cancel',owner=True)
                elif action=='cleanup':await asyncio.to_thread(store.cleanup)
                elif action=='clear_context':
                    if self.client:
                        self.client.runtime.invalidate_guild(gid)
                elif action!='refresh':raise ValueError('Unknown companion action')
                await self.refresh_companion(gid,user,kwargs.get('query',''),kwargs.get('kind'))
                self.notice='로컬 기록을 확인했어요' if action=='refresh' else '변경을 적용했어요'
            elif operation=='visual_cache':
                gid=int(kwargs['guild'])
                if not self.known_guild(gid):raise PermissionError('Unknown guild')
                from .vision import VisualCache,download
                cache=self.client.cache if self.client else VisualCache(ROOT/'visual.sqlite3')
                if not kwargs.get('refresh'):
                    await asyncio.to_thread(cache.clear,gid);self.notice='선택한 서버의 시각 캐시를 비웠어요'
                else:
                    channel_id=int(kwargs['channel']);cfg=self.settings.get()
                    if not self.client or not self.client.is_ready() or not cfg['vision']:raise ValueError('연결과 실험 시각 분석 활성화가 필요해요')
                    channel=self.client.get_channel(channel_id)
                    parent=getattr(channel,'parent_id',None)
                    if not channel or channel.guild.id!=gid or scope(cfg,gid,channel_id,parent)=='silent':raise PermissionError('Allowed channel required')
                    client=self.client;task=asyncio.current_task();client.owner_tasks.add(task)
                    try:
                        for asset in [*channel.guild.emojis,*channel.guild.stickers][:5]:
                            current=self.settings.get()
                            if self.client is not client or client.runtime.stopped or not current['vision'] or scope(current,gid,channel_id,parent)=='silent':break
                            await cache.analyze(gid,('emoji:' if hasattr(asset,'animated') else 'sticker:')+str(asset.id),await download(str(asset.url)),client.backend,force=True)
                    finally:client.owner_tasks.discard(task)
                    self.notice='실험 시각 캐시를 최대 5개 다시 분석했어요'
            elif operation=='diagnostics':
                from .settings import atomic_private_json
                from .telemetry import summarize
                from collections import Counter
                runtime=self.client.runtime if self.client else None
                atomic_private_json(ROOT/'diagnostic-report.json',dict(schema=1,
                    connected=bool(self.client and self.client.is_ready()),
                    queue_depth=self.client.backend.pending if self.client else 0,
                    gpu_scheduler=self.client.backend.scheduler.snapshot() if self.client and hasattr(self.client.backend,'scheduler') else {},
                    safe_stopped=runtime.stopped if runtime else False,
                    summary=summarize(runtime.traces if runtime else []),
                    assembly_events=runtime.utterances.report() if runtime else [],
                    storage=dict(schema=getattr(getattr(self,'companion',None),'schema_version',None),error=getattr(getattr(self,'companion',None),'last_error',None)),
                    commands=dict(reviewed=bool(getattr(self,'command_review',None)),pending=bool(self.settings.get()['command_sync_pending']),
                        state=getattr(self.client,'command_status',{}) if self.client else {}),
                    codes=dict(Counter(r['code'] for r in runtime.diagnostics)) if runtime else {}))
                self.notice='진단 보고서 저장 · local_data/bot/diagnostic-report.json'
            elif operation=='guild':
                gid=kwargs['guild']
                if not self.known_guild(gid):raise PermissionError('Guild is not connected')
                def toggle(cfg):
                    g=cfg['guilds'].setdefault(str(gid),dict(enabled=False,channels={},threads={}))
                    g['enabled']=not g['enabled']
                self.settings.change(owner,toggle)
                if self.client:self.client.runtime.invalidate_all()
            elif operation=='scope':
                gid=kwargs['guild'];cid=kwargs['channel']
                if not self.known_guild(gid):raise PermissionError('Guild is not connected')
                from .settings import positive_id
                positive_id(gid);positive_id(cid)
                def apply_scope(cfg):
                    g=cfg['guilds'].setdefault(str(gid),dict(enabled=False,channels={},threads={}))
                    g['threads' if kwargs['thread'] else 'channels'][str(cid)]=dict(
                        mode=kwargs['text_mode'],reaction_mode=kwargs['reaction_mode'],inherit=kwargs['inherit'])
                    g['enabled']=kwargs['enabled']
                self.settings.change(owner,apply_scope)
                if self.client:
                    self.client.runtime.invalidate(cid)
                    guild=self.client.get_guild(gid)
                    if guild:
                        for thread in guild.threads:
                            if thread.parent_id==cid:self.client.runtime.invalidate(thread.id)
            else:raise ValueError('Unknown operation')
            if operation in {'settings','scope','guild'}:self.notice='설정 저장 완료'
        except Exception as exc:
            success=False
            command_errors={'Command review required':'먼저 명령 목록을 확인하고 변경 내용을 승인해 주세요','Command list changed; review again':'명령 목록이 바뀌었어요. 변경 내용을 다시 확인해 주세요','Command verification failed':'명령 정리 결과를 확인하지 못했어요. 목록을 다시 확인해 주세요','Application identity unavailable':'연결된 봇의 애플리케이션을 확인하지 못했어요','Wrong application':'다른 애플리케이션의 명령은 변경하지 않아요'}
            if operation in ('command_review','command_apply'):self.command_review=getattr(self.client,'command_review',None)
            safe={'본인의 친밀도 저장 동의가 필요해요','본인의 기억 저장 동의가 필요해요','연결과 실험 시각 분석 활성화가 필요해요','미리보기 정리에 실패했어요. 앱을 닫고 다시 열어 주세요.'}
            safe.add('봇 연결 후 명령 목록을 확인해 주세요')
            from .processes import ResourceLimitError,resource_message
            self.error=resource_message(exc,NO_RESPONSE.get('resource_stop_'+exc.reason,'모델 준비에 필요한 자원이 부족해요')) if isinstance(exc,ResourceLimitError) else str(exc) if str(exc) in safe else '설정값이나 설치 파일을 확인해 주세요' if isinstance(exc,ValueError) else type(exc).__name__
            if operation in ('command_review','command_apply') and str(exc) in command_errors:self.error=command_errors[str(exc)]
            if operation in ('command_review','command_apply'):
                from discord import HTTPException
                if isinstance(exc,HTTPException):
                    self.error=('명령 API 접근 권한을 확인하지 못했어요' if exc.status==403 else '명령 API 대상을 찾지 못했어요' if exc.status==404 else '명령 API 요청에 실패했어요')+' · 자동 재시도하지 않았어요. 목록을 다시 조회해 주세요'
                elif str(exc) in {'Wrong command scope','Unexpected local command contract','Application connection changed'}:
                    self.error='명령의 애플리케이션·등록 범위를 다시 확인해 주세요. 변경을 완료한 것으로 간주하지 마세요'
            self.last_management_error=dict(operation=operation,kind=type(exc).__name__,message=self.error,at=time.time())
            if operation=='preview':self.preview_rejection=dict(session=kwargs.get('session'),error=self.error)
        result=dict(ok=success,error='' if success else self.error)
        self._publish()
        return result

    async def refresh_companion(self,guild,user=None,query='',kind=None):
        self.companion_request=getattr(self,'companion_request',0)+1;request=self.companion_request
        self.companion_loading=True;self._publish()
        def read():
            store=self.companion
            memories=store.memories(guild,user,query=query,kind=kind,include_expired=True)
            reminders=store.reminders(guild,user)
            people={r['user']:dict(r) for r in store.users(guild)}
            for uid in store.consent_users(guild):people.setdefault(uid,dict(user=uid,affinity=50,interactions=0,last_at=0))
            aliases=store.aliases(guild,user=user)
            for row in aliases:people.setdefault(row['user'],dict(user=row['user'],affinity=50,interactions=0,last_at=0))
            for row in [*store.memories(guild,include_expired=True),*store.reminders(guild)]:
                uid=row.get('user',row.get('requester'))
                people.setdefault(uid,dict(user=uid,affinity=50,interactions=0,last_at=0))
            for person in people.values():person['consent']=store.consent(guild,int(person['user']))
            return dict(guild=guild,user=user,people=list(people.values()),aliases=aliases,memories=memories,reminders=reminders,query=query,kind=kind,history=store.relationship_history(guild,user) if user else [],summaries=store.summaries(guild,int(user)) if user else [],digests=store.digests(guild,int(user),include_expired=True) if user else [])
        try:view=await asyncio.to_thread(read)
        except Exception:
            if request==self.companion_request:self.companion_loading=False;self.companion_view=dict(guild=guild,user=user,load_error=True)
            raise
        if request!=self.companion_request:return
        self.companion_loading=False
        self.companion_view=view
        names=getattr(self.client,'user_names',{}) if self.client else {}
        if self.client:
            for (g,ch,uid),(observed,at) in self.client.runtime.members.people.items():
                if g==guild and str(uid) not in {p['user'] for p in view['people']}:view['people'].append(dict(user=str(uid),affinity=50,interactions=0,last_at=0))
        for person in self.companion_view['people']:person['label']=names.get((guild,int(person['user'])),f"사용자 {person['user']}")

    async def _run_bot(self):
        self.starting_model=True
        try:
            self.phase='모델 준비 중 — 첫 연결은 약 40초'
            from .inference import LocalBackend
            from .discord_app import EchoClient
            logging.getLogger('discord').setLevel(logging.CRITICAL)
            from .settings import DEFAULTS
            cfg=self.settings.get() if self.settings else dict(DEFAULTS)
            self.client=EchoClient(self.settings,LocalBackend(model_id=cfg['model'],model_roots=cfg['model_roots'] or None),self.bootstrap['admin_guilds'],companion=self.companion)
            await self.client.backend.ready()
            if hasattr(self.client.backend,'probe'):await self.client.backend.probe()
            self.starting_model=False
            self.phase='Discord 연결 중'
            task=asyncio.create_task(self.client.start(self.bootstrap['token'],reconnect=True))
            try:
                while not task.done():
                    self.phase='연결됨' if self.client.is_ready() else '연결·재연결 중'
                    await asyncio.sleep(.4)
                await task
            finally:
                task.cancel();await asyncio.gather(task,return_exceptions=True)
        except asyncio.CancelledError:raise
        except Exception as exc:
            from .processes import ResourceLimitError,resource_message
            self.error=resource_message(exc,NO_RESPONSE.get('resource_stop_'+exc.reason,'모델 준비에 필요한 자원이 부족해요')) if isinstance(exc,ResourceLimitError) else type(exc).__name__
        finally:
            self.starting_model=False
            if self.client:
                from .settings import atomic_private_json
                client=self.client
                try:
                    # Resource release must happen even with a full/read-only disk.
                    await client.close()
                except Exception as exc:self.error="Shutdown"+type(exc).__name__
                finally:
                    self.client=None
                    try:
                        self.last_jobs=client.runtime.monitor();self.last_statistics=client.runtime.ledger.statistics()
                    except (AttributeError,OSError,sqlite3.Error):pass
                    try:atomic_private_json(ROOT/'desktop-performance.json',client.backend.metrics)
                    except OSError:self.error='PerformanceWriteError'
            self.phase='정지'
            self._published_at=0;self._publish()


from .desktop_ui import DesktopApp


def main():
    import argparse
    import sys
    # pythonw has no standard streams. Keep library progress/errors private.
    ROOT.mkdir(parents=True,exist_ok=True)
    if sys.stderr is None:sys.stderr=(ROOT/'desktop-console.log').open('a',encoding='utf-8')
    if sys.stdout is None:sys.stdout=sys.stderr
    parser=argparse.ArgumentParser();parser.add_argument('--start',action='store_true');args=parser.parse_args()
    root=tk.Tk();controller=LocalController();DesktopApp(root,controller)
    if args.start:
        def start_when_ready():
            if controller.loop and getattr(controller,'settings',None):controller.submit('start')
            else:root.after(400,start_when_ready)
        root.after(400,start_when_ready)
    root.mainloop()


if __name__=='__main__':main()
