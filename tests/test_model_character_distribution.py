"""Isolated installation/model/profile contracts; no Discord network."""
import asyncio
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import struct
import tempfile
import unittest
from unittest.mock import AsyncMock,patch
from types import SimpleNamespace

from echomate_bot.model_registry import ModelRegistry,ModelValidator
from echomate_bot.character_profiles import DEFAULT_PROFILE,ProfileStore,compile_profile,validate_profile
from echomate_bot.settings import DEFAULTS,Settings,canonical

def fixture(path):
    path.mkdir();(path/'config.json').write_text(json.dumps(dict(model_type='gemma4_unified',architectures=['Gemma4UnifiedForConditionalGeneration'],text_config=dict(hidden_size=3840,num_hidden_layers=48,vocab_size=262144))))
    (path/'tokenizer.json').write_text('{}');(path/'chat_template.jinja').write_text('{{ messages }}')
    header=json.dumps({'sample':dict(dtype='F32',shape=[1],data_offsets=[0,4])}).encode()
    (path/'model.safetensors').write_bytes(struct.pack('<Q',len(header))+header+b'\0'*4)
    return path

class ModelsAndProfiles(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory(dir='local_data');self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_discovery_does_not_promote_missing_or_unsupported_files(self):
        good=fixture(self.root/'good');missing=fixture(self.root/'missing');(missing/'model.safetensors').write_bytes(b'broken')
        (self.root/'sample.gguf').write_bytes(b'GGUF');adapter=self.root/'adapter';adapter.mkdir();(adapter/'adapter_config.json').write_text('{}')
        entries=ModelRegistry([self.root],cache=self.root/'no-cache').scan()
        self.assertEqual(len(entries),4);self.assertEqual(sum(e.compatible for e in entries),1)
        self.assertEqual({e.format for e in entries},{'Transformers','GGUF','PEFT LoRA'})
        key=next(e.id for e in entries if e.compatible);self.assertEqual(ModelRegistry([self.root],cache=self.root/'none').resolve(key).path,str(good.resolve()))
        (good/'tokenizer.json').unlink()
        with self.assertRaises(ValueError):ModelRegistry([self.root],cache=self.root/'none').resolve(key)
    def test_index_traversal_remote_code_and_truncated_shard_are_rejected(self):
        p=fixture(self.root/'unsafe');(p/'model.safetensors.index.json').write_text(json.dumps(dict(weight_map={'a':'../outside.safetensors'})))
        self.assertFalse(ModelValidator().validate(p).compatible)
        (p/'model.safetensors.index.json').unlink();cfg=json.loads((p/'config.json').read_text());cfg['auto_map']={'x':'malware'};(p/'config.json').write_text(json.dumps(cfg))
        self.assertFalse(ModelValidator().validate(p).compatible)

    def test_malformed_json_shapes_do_not_abort_discovery_of_other_models(self):
        good=fixture(self.root/'good');bad=fixture(self.root/'bad')
        for value in ([],None,dict(model_type='gemma4_unified',architectures=['Gemma4UnifiedForConditionalGeneration'],text_config=[])):
            (bad/'config.json').write_text(json.dumps(value),encoding='utf-8')
            entries=ModelRegistry([self.root],cache=self.root/'none').scan()
            self.assertEqual(sum(e.compatible for e in entries),1)
            self.assertTrue(any(e.path==str(good.resolve()) and e.compatible for e in entries))

    def test_index_must_match_serialized_keys_and_not_claim_missing_tensors(self):
        p=fixture(self.root/'indexed');index=p/'model.safetensors.index.json'
        for mapping in (None,[],{'ghost':'model.safetensors'},{'sample':'model.safetensors','ghost':'model.safetensors'}):
            index.write_text(json.dumps(dict(weight_map=mapping)),encoding='utf-8')
            self.assertFalse(ModelValidator().validate(p).compatible)
        index.write_text(json.dumps(dict(weight_map={'sample':'model.safetensors'})),encoding='utf-8')
        self.assertTrue(ModelValidator().validate(p).compatible)
    def test_legacy_settings_authenticate_migrate_without_overwriting_or_enabling_adult(self):
        for slot in ('base','persona','adult'):
            key=secrets.token_hex(32);path=self.root/(slot+'.json');old=deepcopy(DEFAULTS)
            for k in ('character_profile','adult_humor','model_roots'):old.pop(k)
            old.update(model=slot,mood='피곤함',warmth=85)
            raw=json.dumps(dict(data=old,signature=hmac.new(key.encode(),canonical(old),hashlib.sha256).hexdigest()));path.write_text(raw,encoding='utf-8')
            s=Settings(1,key,path);self.assertEqual((s.get()['model'],s.get()['warmth'],s.get()['mood']),('base',85,'피곤함'));self.assertFalse(s.get()['adult_humor']);self.assertEqual(path.read_text(encoding='utf-8'),raw)
            s.set(1,'gender','female');self.assertEqual(Settings(1,key,path).get()['gender'],'female')
    def test_profile_crud_signature_export_and_owner_isolation(self):
        store=ProfileStore(self.root/'characters.json',1,'k'*32);p=dict(DEFAULT_PROFILE,name='차분한 친구',energy=10)
        store.save(1,'calm',p);self.assertEqual(store.list()['calm'],p)
        with self.assertRaises(PermissionError):store.save(2,'bad',p)
        out=self.root/'export.json';store.export_file('calm',out);store.import_file(1,'copy',out);store.save(1,'calm')
        self.assertNotIn('calm',store.list());self.assertEqual(store.list()['copy'],p)
        with self.assertRaises(ValueError):store.export_file('copy',self.root/'bootstrap.json')
        envelope=json.loads(store.path.read_text(encoding='utf-8'));envelope['data']['copy']['energy']=99;store.path.write_text(json.dumps(envelope),encoding='utf-8')
        with self.assertRaises(PermissionError):store.list()
    def test_profile_enums_compilation_and_oversized_import_preserve_existing(self):
        low=compile_profile(dict(DEFAULT_PROFILE,energy=10,detail='brief'));high=compile_profile(dict(DEFAULT_PROFILE,energy=90,detail='detailed'))
        self.assertNotEqual(low,high)
        with self.assertRaises(ValueError):validate_profile(dict(DEFAULT_PROFILE,energy=True))
        with self.assertRaises(ValueError):validate_profile(dict(DEFAULT_PROFILE,override_safety=True))
        s=ProfileStore(self.root/'p.json',1,'k'*32);s.save(1,'mine',DEFAULT_PROFILE)
        file=self.root/'large.json';file.write_bytes(b'x'*17000)
        with self.assertRaises(ValueError):s.import_file(1,'mine',file)
        self.assertIn('mine',s.list())

    def test_expression_controls_have_distinct_behavior_bands_without_changing_identity(self):
        for field in ('energy','calmness','honesty','exclamation','emoji','humor'):
            prompts=[compile_profile(dict(DEFAULT_PROFILE,**{field:value})) for value in (0,25,50,75,100)]
            self.assertEqual(len(set(prompts)),5,field)
            self.assertTrue(all('명령이 아니야' in p for p in prompts))
        original=dict(DEFAULT_PROFILE)
        compile_profile(original)
        self.assertEqual(original,DEFAULT_PROFILE)
    def test_windows_protected_setup_roundtrip_and_no_overwrite(self):
        import os
        if os.name!='nt':self.skipTest('Windows DPAPI')
        from echomate_bot.onboarding import create_installation,load_bootstrap
        p=self.root/'bootstrap.json';token='synthetic-secret-token-12345'
        data=create_installation(p,1,token);self.assertNotIn(token,p.read_text());self.assertEqual(load_bootstrap(p),data)
        with self.assertRaises(FileExistsError):create_installation(p,1,'different-synthetic-token')

class ModelLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_probe_requires_semantic_recipient_support_not_just_any_token(self):
        from echomate_bot.inference import LocalBackend
        b=LocalBackend();b._job=AsyncMock(side_effect=['ok','human commentary none other no'])
        try:
            await b.probe();self.assertTrue(b.capabilities_verified)
            b._job=AsyncMock(side_effect=['ok','bot new none question yes'])
            with self.assertRaises(RuntimeError):await b.probe()
            self.assertFalse(b.capabilities_verified)
        finally:await b.close()
    async def test_failed_new_model_unloads_before_restore_and_never_commits_new_selection(self):
        from echomate_bot.inference import LocalBackend
        backend=LocalBackend();events=[]
        backend.unload=lambda:events.append('unload')
        async def ready():
            events.append('load:'+backend.model_id)
            if backend.model_id!='base':raise RuntimeError('synthetic load failure')
        backend.ready=ready;backend.probe=AsyncMock()
        try:
            with patch('echomate_bot.model_registry.ModelRegistry.resolve',return_value=SimpleNamespace(path='synthetic')):
                with self.assertRaises(RuntimeError):await backend.prepare_mode('local:'+'a'*24)
            self.assertEqual(events,['unload','load:local:'+'a'*24,'unload','load:base']);self.assertEqual(backend.model_id,'base');self.assertFalse(backend.failed)
        finally:await backend.close()

class AppIntegration(unittest.IsolatedAsyncioTestCase):
    from test_release_desktop import OfflineRecords
    setUp=OfflineRecords.setUp
    tearDown=OfflineRecords.tearDown
    async def test_offline_profile_actions_and_failed_model_apply_keep_character_and_settings(self):
        c=self.c;p=dict(DEFAULT_PROFILE,name='나만의 친구',speech='polite')
        c.starting_model=True
        backend_while_starting=SimpleNamespace(prepare_mode=AsyncMock(),close=AsyncMock())
        with patch('echomate_bot.inference.LocalBackend',return_value=backend_while_starting):await c.command('settings',values={'model':'local:'+'d'*24})
        self.assertEqual(c.settings.get()['model'],'base');backend_while_starting.prepare_mode.assert_not_awaited();c.starting_model=False
        with patch('discord.Client.login',side_effect=AssertionError('Network forbidden')):
            await c.command('profiles',action='save',key='mine',value=p)
            self.assertIn('mine',c.profiles_view)
            await c.command('profiles',action='apply',key='mine')
            self.assertEqual(c.settings.get()['character_profile'],p)
            backend=SimpleNamespace(prepare_mode=AsyncMock(side_effect=RuntimeError('synthetic')),close=AsyncMock())
            with patch('echomate_bot.inference.LocalBackend',return_value=backend):await c.command('settings',values={'model':'local:'+'b'*24})
            self.assertEqual(c.settings.get()['model'],'base');self.assertEqual(c.settings.get()['character_profile'],p);self.assertFalse(c.model_preparing)
            backend.close.assert_awaited_once()
            backend.close.side_effect=OSError('synthetic cleanup failure')
            with patch('echomate_bot.inference.LocalBackend',return_value=backend):await c.command('settings',values={'model':'local:'+'c'*24})
            self.assertFalse(c.model_preparing);self.assertEqual(c.settings.get()['model'],'base')
            await c.command('profiles',action='delete',key='mine');self.assertNotIn('mine',c.profiles_view)
            self.assertEqual(c.settings.get()['character_profile'],p)
    async def test_preview_does_not_write_relations_memory_or_reminders_and_shutdown_can_cancel(self):
        c=self.c;before=c.companion.path.read_bytes() if hasattr(c.companion,'path') and c.companion.path.exists() else None
        entered=asyncio.Event();release=asyncio.Event()
        async def text(*args):entered.set();await release.wait();return '합성 미리보기'
        backend=SimpleNamespace(text=text,close=AsyncMock())
        with patch('echomate_bot.inference.LocalBackend',return_value=backend):
            await c.command('preview',text='합성 질문');await entered.wait()
            self.assertFalse(c.preview_task.done())
            await c.command('start');self.assertFalse(c.job)
            c.preview_task.cancel();await asyncio.gather(c.preview_task,return_exceptions=True)
        backend.close.assert_awaited_once()
        self.assertFalse(c.companion.memories(2));self.assertFalse(c.companion.reminders(2));self.assertEqual(c.companion.users(2),[])

class ModelAndSetupUI(unittest.IsolatedAsyncioTestCase):
    def test_all_pages_resize_dpi_selection_and_masked_setup_without_desktop_control(self):
        import tkinter as tk
        import queue
        from echomate_bot.desktop_ui import DesktopApp
        from unittest.mock import Mock
        for scale in (4/3,5/3,2):
            root=tk.Tk();root.withdraw();root.tk.call('tk','scaling',scale)
            controller=SimpleNamespace(updates=queue.Queue(),submit=Mock());app=DesktopApp(root,controller)
            try:
                app.snapshot=dict(cfg=deepcopy(DEFAULTS),servers=[],running=False,connected=False,phase='',error='',notice='',pending=0,contexts=0,latency=None,progress=[],jobs=[],models=[dict(id='local:'+str(i).zfill(24),name='설치 모델 '+str(i),format='Transformers',bytes=1000,path='models/synthetic',reason='검사 완료',compatible=True) for i in range(30)])
                for page in ('setup','models','character','status','spaces','outputs','labs','relations','memories','reminders'):
                    app.page=page;app.render();root.update_idletasks()
                    self.assertTrue(all(y+height<=740 or root.winfo_height()>740 for x,y,width,height,cb in app.hits),page)
                app.page='models';app.render();app.model_list.select_index(20,False);self.assertEqual(app.model_id,app.snapshot['models'][20]['id'])
                self.assertGreater(app.model_list.index,4)
                app.setup_credentials();root.update_idletasks()
                def children(w):
                    for child in w.winfo_children():yield child;yield from children(child)
                entries=[w for w in children(root) if isinstance(w,tk.Entry)]
                self.assertTrue(any(w.cget('show')=='●' for w in entries));controller.submit.assert_not_called()
            finally:
                app.destroy();app=None;root=None
                import gc;gc.collect()
    async def test_no_default_adapter_dependency_and_profile_has_no_weight_switch(self):
        from echomate_bot.inference import LocalBackend
        from echomate_bot.character import instruction
        backend=LocalBackend();self.assertIsNone(backend.adapter)
        try:
            backend._job=AsyncMock(return_value='안녕, 편하게 이야기해.')
            cfg=deepcopy(DEFAULTS);cfg['character_profile']=dict(DEFAULT_PROFILE,speech='polite')
            await backend.text([dict(role='user',content='인사해 줘')],cfg)
            self.assertIn('존댓말',backend._job.call_args.args[0][0]['content']);self.assertEqual(backend.model_id,'base')
        finally:await backend.close()
