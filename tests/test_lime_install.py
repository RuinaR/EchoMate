"""Pinned provisioning, cancellation and hostile archive boundaries; no network."""
import asyncio
import hashlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from echomate_bot.lime_install import Asset, LimeInstall, approved_url


DATA = b'synthetic-lime'
ASSET = Asset('fixture.gguf', 'https://huggingface.co/example/fixture',
              len(DATA), hashlib.sha256(DATA).hexdigest())


class Reply:
    def __init__(self, data, status=200, headers=None, callback=None):
        self.data = data;self.status = status;self.headers = headers or {};self.content = self
        self.callback = callback
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def iter_chunked(self,size):
        for block in (self.data[:4], self.data[4:]):
            if block:yield block
            if self.callback:self.callback()


class Session:
    def __init__(self,replies):self.replies=list(replies);self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append((url,kwargs));return self.replies.pop(0)


class Provisioning(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='local_data')
        self.root=Path(self.temp.name);self.install=LimeInstall(self.root)
    async def asyncTearDown(self):self.temp.cleanup()

    async def test_resumes_exact_range_and_hashes_before_publish(self):
        (self.root/'fixture.gguf.part').write_bytes(DATA[:4])
        session=Session([Reply(DATA[4:],206,{'Content-Range':f'bytes 4-{len(DATA)-1}/{len(DATA)}'})])
        output=await self.install.download(session,ASSET)
        self.assertEqual(output.read_bytes(),DATA)
        self.assertEqual(session.calls[0][1]['headers']['Range'],'bytes=4-')
        self.assertFalse((self.root/'fixture.gguf.part').exists())

    async def test_server_ignores_range_restarts_without_appending(self):
        (self.root/'fixture.gguf.part').write_bytes(DATA[:4])
        output=await self.install.download(Session([Reply(DATA)]),ASSET)
        self.assertEqual(output.read_bytes(),DATA)

    async def test_bad_range_or_hash_never_creates_installed_file(self):
        session=Session([Reply(DATA,206,{'Content-Range':'bytes 1-9/10'})])
        with self.assertRaises(ValueError):await self.install.download(session,ASSET)
        with self.assertRaises(ValueError):
            await self.install.download(Session([Reply(b'x'*len(DATA))]),ASSET)
        self.assertFalse((self.root/'fixture.gguf').exists())
        self.assertTrue((self.root/'fixture.gguf.part').exists())

    async def test_cancellation_preserves_only_partial_and_retry_resumes(self):
        session=Session([Reply(DATA,callback=self.install.cancelled.set)])
        with self.assertRaises(asyncio.CancelledError):await self.install.download(session,ASSET)
        self.assertEqual((self.root/'fixture.gguf.part').read_bytes(),DATA[:4])
        self.assertFalse((self.root/'fixture.gguf').exists())

    async def test_unapproved_redirect_and_no_license_never_download(self):
        with self.assertRaises(PermissionError):await self.install.install()
        with self.assertRaises(ValueError):
            await self.install.download(Session([Reply(b'',302,{'Location':'http://127.0.0.1/private'})]),ASSET)
        for url in ('file:///secret','https://huggingface.co.evil.test/a','https://user:pass@github.com/a'):
            with self.assertRaises(ValueError):approved_url(url)

    async def test_corrupt_existing_model_is_preserved_and_disk_reserve_is_enforced(self):
        output=self.root/'fixture.gguf';output.write_bytes(b'bad')
        with self.assertRaises(ValueError):await self.install.download(Session([]),ASSET)
        self.assertEqual(output.read_bytes(),b'bad')
        output.unlink()
        with patch('echomate_bot.lime_install.shutil.disk_usage',return_value=SimpleNamespace(free=0)):
            with self.assertRaises(OSError):await self.install.download(Session([]),ASSET)

    async def test_import_preserves_source_and_atomic_publish(self):
        source=self.root/'original.gguf';source.write_bytes(DATA)
        output=await self.install.blocking(self.install.copy_asset,source,ASSET)
        self.assertEqual(source.read_bytes(),DATA);self.assertEqual(output.read_bytes(),DATA)
        with self.assertRaises(ValueError):
            await self.install.blocking(self.install.copy_asset,source,Asset('bad.gguf',ASSET.url,len(DATA),'0'*64))
        self.assertFalse((self.root/'bad.gguf').exists())

    async def test_worker_cancellation_drains_before_next_operation(self):
        import threading,time
        entered=threading.Event();finished=threading.Event()
        def work():
            entered.set()
            while not self.install.cancelled.is_set():time.sleep(.005)
            finished.set();raise InterruptedError()
        task=asyncio.create_task(self.install.blocking(work))
        await asyncio.to_thread(entered.wait)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertTrue(finished.is_set())

    def test_archive_traversal_and_symlink_are_rejected_without_writing_outside(self):
        for index,name in enumerate(('../escape','C:/escape','folder\\escape','NUL','folder./file')):
            archive=self.root/f'hostile{index}.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'bad')
            with self.assertRaises(ValueError):self.install.extract_engine([archive])
            self.assertFalse((self.root/'engine-b11721.installing').exists())

    async def test_engine_manifest_detects_modified_dependency(self):
        from echomate_bot.settings import atomic_private_json
        engine=self.root/'engine-b11721';engine.mkdir()
        (engine/'llama-server.exe').write_bytes(b'exe');(engine/'library.dll').write_bytes(b'dll')
        (self.root/'fixture.gguf').write_bytes(DATA)
        records={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in engine.iterdir()}
        atomic_private_json(engine/'files.json',records)
        with patch('echomate_bot.lime_install.MODEL',ASSET),patch('echomate_bot.lime_install.ENGINE_SHA256',records['llama-server.exe']):
            executable,model=await self.install.verify()
            self.assertEqual(executable,(engine/'llama-server.exe').resolve())
            (engine/'library.dll').write_bytes(b'tampered')
            with self.assertRaises(ValueError):await self.install.verify()

    async def test_explicit_repair_preserves_corrupt_partial_and_original(self):
        original=self.root/'original';original.write_bytes(DATA)
        (self.root/ASSET.name).write_bytes(b'corrupt')
        (self.root/(ASSET.name+'.part')).write_bytes(DATA[:4])
        with patch('echomate_bot.lime_install.MODEL',ASSET):
            with self.assertRaises(PermissionError):await self.install.repair()
            await self.install.repair(confirmed=True)
        self.assertEqual(original.read_bytes(),DATA)
        self.assertEqual((self.root/(ASSET.name+'.rejected')).read_bytes(),b'corrupt')
        self.assertEqual((self.root/(ASSET.name+'.part.rejected')).read_bytes(),DATA[:4])
        self.assertEqual((await self.install.download(Session([Reply(DATA)]),ASSET)).read_bytes(),DATA)

    async def test_repair_mid_failure_rolls_back_owned_moves(self):
        import os
        a=self.root/ASSET.name;b=self.root/(ASSET.name+'.part')
        a.write_bytes(b'bad');b.write_bytes(b'part')
        real=os.rename;count=0
        def rename(source,target):
            nonlocal count
            count+=1
            if count==2:raise PermissionError('fixture')
            return real(source,target)
        with patch('echomate_bot.lime_install.MODEL',ASSET),patch('echomate_bot.lime_install.os.rename',side_effect=rename):
            with self.assertRaises(PermissionError):await self.install.repair(confirmed=True)
        self.assertEqual(a.read_bytes(),b'bad');self.assertEqual(b.read_bytes(),b'part')
        self.assertFalse((self.root/(ASSET.name+'.rejected')).exists())
