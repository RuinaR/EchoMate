"""Lime Windows product entry. Separate data; same process serving lease.

No Discord API is called by install, verify, name, load or local preview.
The existing explicit Start path is reachable only after model qualification.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import tkinter as tk

from .desktop import LocalController
from .desktop_ui import DesktopApp, PAGES, PANEL, MUTED, ACCENT, rounded
from .character_models import CharacterNames, valid_name
from .character_store import CharacterStores
from .gguf_backend import GGUFLocalBackend
from .lime_install import LimeInstall, LICENSE_NOTICE
from .settings import ROOT, private_path


class LimeController(LocalController):
    def __init__(self, *, data_root=None):
        root = private_path(data_root or ROOT/'lime')
        self.lime = dict(stage='not_installed', busy=False, name='라임', error=None,
                         done=0, total=0, local_result='')
        self.lime_backend = None
        self.lime_diagnostics = {}
        self.lime_task = None
        self.installer = LimeInstall(root/'install', progress=self._install_progress)
        from .lime_install import MODEL
        if (root/'install'/MODEL.name).exists():
            self.lime['stage'] = 'present_unverified'
        try:
            self.names = CharacterNames(root/'character-names.json')
            self.lime['name'] = self.names.effective('lime')
        except (OSError, ValueError):
            self.names = None
            self.lime.update(stage='failed', error='이름 파일을 읽지 못했어요. 원본을 보존하고 백업을 확인해 주세요.')
        super().__init__(data_root=root)

    def discover_models(self):
        return []  # Catalog diagnostics remain available outside the main flow.

    def open_companion(self):
        path = self.data_root/'companion.sqlite3'
        hub = CharacterStores(path) if path.exists() else CharacterStores.create(path)
        return hub.for_character('lime')

    def _install_progress(self, value):
        self.lime.update(value)

    def _publish(self):
        backend = self.lime_backend
        if backend and (backend.failed or getattr(backend.engine, 'failed', False)):
            self.lime.update(stage='recovery_required')
        super()._publish()

    def extra_snapshot(self):
        engine = getattr(self.lime_backend, 'engine', None)
        samples = getattr(engine, 'samples', ())
        latest = samples[-1] if samples else self.lime_diagnostics.get('last_sample')
        return dict(lime=dict(self.lime, resident=self.lime_backend is not None, resources=latest))

    async def _main(self):
        try:
            await super()._main()
        finally:
            await self._cancel_lime()
            if self.lime_backend and not self.client:
                await self.lime_backend.close()
                self.lime_backend = None

    async def _run_bot(self):
        try:
            await super()._run_bot()
        finally:
            if self.lime_backend:
                if await self.lime_backend.reclaimed():
                    self.lime_backend = None
                    self.lime.update(stage='installed')
                else:
                    self.lime.update(stage='recovery_required')

    async def create_backend(self, cfg):
        backend = self.lime_backend
        if not backend or not backend.capabilities_verified or self.lime['stage'] != 'ready':
            raise RuntimeError('Lime 모델 검증을 먼저 완료해 주세요')
        return backend

    async def _cancel_lime(self):
        task = self.lime_task
        self.installer.cancelled.set()
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.lime_task = None

    async def command(self, operation, **kwargs):
        if operation == 'start' and (not self.lime_backend or
                not self.lime_backend.capabilities_verified or self.lime.get('stage') != 'ready'):
            return dict(ok=False, error='Lime 모델 준비 검증을 먼저 완료해 주세요')
        if operation in ('shutdown', 'stop'):
            await self._cancel_lime()
            if operation == 'shutdown' and self.lime_backend and not self.client:
                await self.lime_backend.close()
                self.lime_backend = None
        if operation == 'lime_cancel':
            await self._cancel_lime()
            self.lime.update(busy=False, stage='cancelled')
            self._publish()
            return dict(ok=True, error='')
        if operation.startswith('lime_'):
            if not self.lease:
                return dict(ok=False, error='다른 EchoMate가 실행 자원을 소유하고 있어요')
            if self.lime_task and not self.lime_task.done():
                return dict(ok=False, error='현재 Lime 작업이 끝나거나 취소된 뒤 다시 시도해 주세요')
            if operation in ('lime_install', 'lime_import', 'lime_verify', 'lime_load', 'lime_repair') and (self.client or self.lime_backend):
                return dict(ok=False, error='모델을 먼저 안전하게 해제해 주세요')
            self.lime_task = asyncio.create_task(self._lime_action(operation, kwargs))
            return await self.lime_task
        if operation in ('models', 'profiles', 'preview') or operation == 'settings' and 'model' in kwargs.get('values', {}):
            return dict(ok=False, error='Lime 화면에서 설치·이름·모델 실행을 관리해 주세요')
        # Display-name edits must never call the Discord profile/nickname API.
        if operation == 'name':
            return dict(ok=False, error='Lime 이름은 모델 화면에서 변경해 주세요')
        return await super().command(operation, **kwargs)

    async def _lime_action(self, operation, values):
        prior_stage = self.lime.get('stage')
        self.lime.update(busy=True, error=None)
        self.error = ''
        self.installer.cancelled.clear()
        backend = None
        try:
            if operation in ('lime_install', 'lime_import', 'lime_verify', 'lime_load'):
                if self.client or self.lime_backend:
                    raise RuntimeError('모델을 먼저 안전하게 해제해 주세요')
                if operation == 'lime_install':
                    await self.installer.install(accepted=values.get('accepted') is True)
                elif operation == 'lime_import':
                    await self.installer.import_files(values['model'], values['engine'], values['cuda'],
                                                      accepted=values.get('accepted') is True)
                elif operation == 'lime_verify':
                    await self.installer.verify()
                else:
                    engine, model = await self.installer.verify()
                    if self.names is None:
                        raise ValueError('이름 파일 복구가 필요해요')
                    self.lime.update(stage='loading')
                    self.lime['identity_verified'] = False
                    backend = GGUFLocalBackend(engine, model, self.data_root/'engine-log',
                        name=self.names.effective('lime'), serving_lease=self.lease)
                    await backend.ready()
                    await backend.probe_identity()
                    self.lime['identity_verified'] = True
                    await backend.probe()  # Never bypass semantic qualification.
                    self.lime_backend = backend
                    self.lime.update(stage='ready')
                    backend = None
            elif operation == 'lime_name':
                if getattr(self, 'starting_model', False):
                    raise RuntimeError('모델 시작 검사가 끝난 뒤 이름을 변경해 주세요')
                if self.names is None:
                    raise ValueError('이름 파일 복구가 필요해요')
                name = valid_name(values['name'])
                previous = self.names.effective('lime')
                active = self.client.runtime if self.client else None
                model = self.client.backend if self.client else self.lime_backend
                if active:
                    await active.rename_character(self.bootstrap['owner_id'], name)
                elif model:
                    await model.rename(name)
                try:
                    self.names.save('lime', name)
                except BaseException:
                    if model:
                        try:
                            if active:
                                await active.rename_character(self.bootstrap['owner_id'], previous)
                            else:
                                await model.rename(previous)
                        except BaseException:
                            self.lime['stage'] = 'recovery_required'
                    raise
                self.lime['name'] = name
            elif operation == 'lime_repair':
                await self.installer.repair(confirmed=values.get('confirmed') is True)
            elif operation == 'lime_unload':
                if self.client:
                    raise RuntimeError('Discord 봇을 먼저 정지해 주세요')
                if self.lime_backend:
                    await self.lime_backend.close()
                    self.lime_backend = None
                self.lime['stage'] = 'installed'
            elif operation == 'lime_preview':
                if not self.lime_backend or not self.lime_backend.capabilities_verified:
                    raise RuntimeError('모델 준비 검증을 먼저 완료해 주세요')
                text = values['text']
                if not isinstance(text, str) or not 1 <= len(text) <= 1000:
                    raise ValueError('미리보기 입력은 1~1000자예요')
                cfg = self.settings.get() if getattr(self, 'settings', None) else {}
                self.lime['local_result'] = await self.lime_backend.text(
                    [{'role': 'user', 'content': text}], cfg)
            else:
                raise ValueError('Unknown Lime operation')
            return dict(ok=True, error='')
        except asyncio.CancelledError:
            self.lime.update(stage='cancelled')
            raise
        except Exception as exc:
            from .processes import ResourceLimitError, resource_message
            explanations={
                'Explicit model and runtime license review required':'모델·실행 엔진 이용 조건을 확인하고 동의를 입력해 주세요.',
                'Explicit repair confirmation required':'설치 복구를 진행하려면 복구라고 입력해 주세요.',
                'Pinned file hash mismatch; partial file preserved':'파일 해시가 일치하지 않아요. 부분 파일을 보존했어요. 설치 복구 후 다시 받아 주세요.',
                'Existing file is corrupt; preserve it and select a fresh install folder':'기존 설치 파일이 손상됐어요. 설치 복구로 별도 보존한 뒤 다시 설치해 주세요.',
                'Repair target requires manual backup':'이전 복구 보존본이 있거나 경로가 안전하지 않아요. 기존 보존본을 먼저 별도 백업해 주세요.',
            }
            message = ('청자 판단 품질 검증에 실패했어요. Discord 실행을 허용하지 않았어요.'
                       if str(exc) == 'Model recipient classification validation failed'
                       else resource_message(exc,'PC 자원 보호로 중단했어요 · '+exc.reason) if isinstance(exc,ResourceLimitError)
                       else explanations.get(str(exc),'설치·입력·자원 상태를 확인해 주세요 · '+type(exc).__name__))
            healthy = (operation in ('lime_name', 'lime_preview') and prior_stage == 'ready'
                       and self.lime_backend and self.lime_backend.capabilities_verified
                       and self.lime.get('stage') != 'recovery_required')
            self.lime.update(stage='ready' if healthy else
                             'recovery_required' if self.lime.get('stage') == 'recovery_required' else 'failed',
                             error=message)
            self.error = message
            return dict(ok=False, error=message)
        finally:
            measured = backend or self.lime_backend
            if measured:
                engine = getattr(measured, 'engine', None)
                samples = getattr(engine, 'samples', ())
                self.lime_diagnostics = dict(character_id='lime',
                    identity_verified=self.lime.get('identity_verified', False),
                    capabilities_verified=getattr(measured, 'capabilities_verified', False),
                    load_seconds=getattr(measured, 'load_seconds', None),
                    extrema=dict(getattr(engine, 'extrema', {})),
                    last_sample=samples[-1] if samples else None)
            if backend:
                try:
                    await backend.close()
                    if not await backend.reclaimed():
                        raise RuntimeError('Model reclamation incomplete')
                except BaseException:
                    self.lime_backend = backend
                    self.lime['stage'] = 'recovery_required'
            self.lime['busy'] = False
            self._publish()


STATES = dict(not_installed='설치 확인 전', present_unverified='설치 파일 발견 · 검증 필요',
    downloading='다운로드 중', importing='기존 파일 복사 중',
    verifying='파일 검증 중', extracting='실행 엔진 설치 중', installed='파일 검증 완료 · 모델 로딩 전',
    loading='모델 로딩·품질 검증 중', ready='모델 준비 완료', failed='검증 실패',
    cancelled='작업 취소됨 · 부분 다운로드 보존', recovery_required='자원 정리 확인 필요')


class LimeDesktopApp(DesktopApp):
    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.page = 'lime'

    def navigation(self):
        return [('lime', '라임 · 설치와 이름'), ('setup', 'Discord 설정'), ('spaces', '대화할 곳'),
                ('outputs', '응답 방식'), *PAGES.items(), ('status', '진행 상황')]

    def model_label(self):
        return 'Lime · Q6_K'

    def initial_setup_page(self):
        return 'lime'

    def command_set_label(self):
        return '/동의, /캐릭터'

    def command_privacy_description(self):
        return '/동의는 본인 데이터 동의·철회, /캐릭터는 현재 캐릭터를 본인만 보는 읽기 전용 응답이에요. 캐릭터 변경은 Windows 앱에서만 해요.'

    def page_title(self):
        return '라임과 시작하기' if self.page == 'lime' else super().page_title()

    def can_start(self):
        value = (self.snapshot or {}).get('lime', {})
        return value.get('stage') == 'ready' and not value.get('busy')

    def phase_caption(self, phase):
        if self.page == 'lime':
            return STATES.get((self.snapshot or {}).get('lime', {}).get('stage'), 'Lime 설치를 먼저 확인해 주세요')
        return phase

    def footer_message(self, footer):
        if self.page == 'lime':
            value = (self.snapshot or {}).get('lime', {})
            return ('모델 작업에 실패했어요 · 상태·오류에서 원인을 확인해 주세요' if value.get('error') else
                    '모델 검증 통과 후에만 실행 가능해요 · 실제 Discord 연결은 별도 작업이에요')
        return footer

    def draw_lime(self, w, h, cfg):
        value = (self.snapshot or {}).get('lime', {})
        busy = value.get('busy', False)
        ready = value.get('stage') == 'ready'
        rounded(self.canvas, 226, 143, w-252, h-207, PANEL)
        self.text(250, 164, '① 모델 설치 → ② 이름 설정 → ③ 모델 로딩 → ④ Discord 설정', 10, bold=True, width=w-300)
        self.text(250, 218, 'Lime Q6_K · naksyu/lime_Q6_K · 모델 약 5.8GiB + 실행 엔진', 9, MUTED)
        self.text(250, 246, STATES.get(value.get('stage'), '설치 확인 전'), 11, ACCENT, True)
        self.button(250, 276, 162, 34, '동의하고 다운로드', self.install_dialog, enabled=not busy and not ready)
        self.button(424, 276, 150, 34, '기존 파일 가져오기', self.import_dialog, enabled=not busy and not ready)
        self.button(586, 276, 130, 34, '파일 검증', lambda:self.controller.submit('lime_verify'), enabled=not busy and not ready)
        self.button(728, 276, 130, 34, '작업 취소', lambda:self.controller.submit('lime_cancel'), enabled=busy)
        self.button(870, 276, 110, 34, '설치 복구', self.repair_dialog,
                    enabled=not busy and not value.get('resident', False))
        done = value.get('done', 0);total = value.get('total', 0)
        progress=(f"{value.get('file','모델')} · {done/1024**2:,.0f} / {total/1024**2:,.0f} MiB · {done/total:.1%}" if total else
                  '설치 파일은 별도 사용자 폴더에 저장하며 기존 운영 자료는 자동 이관하지 않아요.')
        self.text(250, 329, self.ellipsize(progress,w-300,9), 9, MUTED)
        resource=value.get('resources') or {}
        if 'free_vram_mib' in resource and 'ram_available' in resource:
            self.text(250, 350, f"최근 측정 · GPU 여유 {resource['free_vram_mib']:,}MiB · RAM 여유 {resource['ram_available']/1024**3:.2f}GiB", 9, MUTED)
        self.text(250, 377, self.ellipsize('현재 이름: '+value.get('name','라임'),320,12), 12, bold=True)
        self.button(600, 371, 150, 34, '이름 변경', self.rename_dialog, enabled=not busy)
        self.button(250, 433, 170, 38, '모델 로딩·검증', lambda:self.controller.submit('lime_load'), primary=True, enabled=not busy and not ready)
        self.button(432, 433, 150, 38, '모델 안전 해제', lambda:self.controller.submit('lime_unload'), enabled=value.get('resident', False) and not busy)
        self.button(594, 433, 170, 38, '로컬 대화 확인', self.preview_dialog, enabled=ready and not busy)
        message=(value.get('error') or value.get('local_result') or
                 '파일 설치와 GPU 로딩은 품질 승인과 달라요. 검증 실패 시 Discord 실행을 막아요.')
        self.text(250, 497, self.ellipsize(message,w-300,10), 10, MUTED)
        self.text(250, 533, '긴 오류는 상단 상태·오류에서, 로컬 답변은 전체 응답에서 확인해 주세요.', 9, MUTED)
        self.button(250, h-150, 170, 34, 'Discord 설정으로', lambda:self.set_page('setup'), enabled=not busy)
        self.button(432, h-150, 150, 34, '라이선스·설치 정보', self.license_dialog)
        self.button(594, h-150, 150, 34, '전체 응답', self.result_dialog, enabled=bool(value.get('local_result')))

    def draw_setup(self, w, h, cfg):
        from .onboarding import GUIDE
        rounded(self.canvas, 226, 143, w-252, h-210, PANEL)
        self.text(250, 166, '라임의 Discord 연결 설정', 14, bold=True)
        self.text(250, 210, '모델 설치와 이름 설정은 라임 화면에서 먼저 진행해 주세요.\n'
                  '봇 정보 등록은 현재 Windows 계정에 암호화해 저장하며 네트워크 인증은 하지 않아요.\n'
                  '기존 운영 설정·기억은 별도 보존되어 있고 자동 이관하지 않아요.', 11, MUTED, width=w-310)
        self.text(250, 314, '실제 연결·서버 조회·명령 변경·송신은 각각 외부 서비스 작업이에요.\n'
                  '모델 검증 실패 중에는 봇 켜기가 비활성화돼요. 마지막 승인 전 자동 실행하지 않아요.',
                  11, MUTED, width=w-310)
        self.text(250, 406, '연결 후 ‘대화할 곳’에서 허용 서버·채널·스레드를 지정하세요.\n'
                  '사용자 동의는 /동의, 현재 정보는 /캐릭터로 확인해요.', 11, MUTED, width=w-310)
        self.button(250, h-190, 190, 36, '봇 정보 등록됨' if cfg else '봇 정보 등록',
                    self.setup_credentials, enabled=not bool(cfg))
        self.button(452, h-190, 150, 36, '라임 설치·이름', lambda:self.set_page('lime'))
        self.button(614, h-190, 180, 36, '연결 준비 안내',
                    lambda:self.form('Discord 연결 준비', [], lambda v:None, GUIDE, read_only=True))

    def license_dialog(self):
        self.form('모델과 실행 엔진의 이용 조건', [('info', '공식 출처와 라이선스', LICENSE_NOTICE)],
                  lambda values: None, '다운로드 전에 각 제공자의 이용 조건을 확인해 주세요.', read_only=True)

    def install_dialog(self):
        self.form('Lime 설치', [('agree', '이용 조건을 확인했다면 동의 입력', '')],
                  lambda values:self.controller.submit('lime_install', accepted=values['agree'].strip() == '동의'),
                  LICENSE_NOTICE)

    def import_dialog(self):
        self.form('검증된 기존 파일에서 설치', [('model', 'Lime GGUF 전체 경로', ''),
                  ('engine', 'b11721 CUDA12.4 실행 엔진 ZIP', ''), ('cuda', '공식 CUDA 런타임 ZIP', ''),
                  ('agree', '이용 조건 확인 후 동의 입력', '')],
                  lambda v:self.controller.submit('lime_import', **{k:v[k] for k in ('model','engine','cuda')},
                      accepted=v['agree'].strip() == '동의'),
                  '원본은 이동/수정하지 않고 사용자 데이터 폴더에 별도 복사해요. '+LICENSE_NOTICE)

    def rename_dialog(self):
        self.form('라임의 이름', [('name', '현재 자기 이름 · 1~32자', (self.snapshot or {}).get('lime', {}).get('name', '라임'))],
                  lambda v:self.controller.submit('lime_name', name=v['name']),
                  'CharacterId·기억·친밀도·동의·예약은 유지해요. Discord 프로필은 바꾸지 않아요.')

    def repair_dialog(self):
        self.form('설치 파일 복구', [('confirm','복구라고 입력하면 손상 파일을 별도 보존','')],
                  lambda v:self.controller.submit('lime_repair',confirmed=v['confirm'].strip()=='복구'),
                  '이 앱 설치 폴더의 손상·부분 파일과 실행 엔진을 .rejected로 보존해요. 기존 가져오기 원본·기억·동의는 건드리지 않아요. 이후 다운로드/가져오기로 다시 설치하세요. 이전 보존본이 있으면 덮어쓰지 않아요.')

    def preview_dialog(self):
        self.form('로컬 대화 확인', [('text', '기억/Discord에 저장하지 않는 입력', '')],
                  lambda v:self.controller.submit('lime_preview', text=v['text']),
                  '모델 준비 검증을 통과한 경우에만 생성해요. 실제 메시지는 보내지 않아요.')

    def result_dialog(self):
        self.form('로컬 응답', [], lambda v:None,
                  (self.snapshot or {}).get('lime',{}).get('local_result') or '아직 로컬 응답이 없어요.', read_only=True)


def main():
    import sys
    root_path = ROOT/'lime'
    root_path.mkdir(parents=True, exist_ok=True)
    if sys.stderr is None:
        sys.stderr = (root_path/'desktop-console.log').open('a', encoding='utf-8')
    if sys.stdout is None:
        sys.stdout = sys.stderr
    root = tk.Tk()
    controller = LimeController()
    LimeDesktopApp(root, controller)
    root.mainloop()


if __name__ == '__main__':
    main()
