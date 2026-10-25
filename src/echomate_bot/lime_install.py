"""Pinned, cancellable Lime provisioning. No Discord, settings or GPU on import."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import threading
from urllib.parse import urlsplit
import zipfile

import aiohttp

from .character_models import character
from .gguf_backend import ENGINE_SHA256
from .settings import atomic_private_json, private_path


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int
    sha256: str


LIME = character('lime')
MODEL = Asset(LIME.model_file,
    f'https://huggingface.co/{LIME.repository}/resolve/{LIME.revision}/{LIME.model_file}',
    LIME.size_bytes, LIME.sha256)
ENGINE = Asset('llama-b11721-bin-win-cuda-12.4-x64.zip',
    'https://github.com/ggml-org/llama.cpp/releases/download/b11721/llama-b11721-bin-win-cuda-12.4-x64.zip',
    267489339, 'a343ee836e03b205881c8add4ebdbac33e49f3662fb3521b44585ca271870748')
CUDA = Asset('cudart-llama-bin-win-cuda-12.4-x64.zip',
    'https://github.com/ggml-org/llama.cpp/releases/download/b11721/cudart-llama-bin-win-cuda-12.4-x64.zip',
    391443627, '8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6')
LICENSE_NOTICE = (
    'Lime / naksyu: Apache-2.0 · llama.cpp: MIT\n'
    'CUDA 12.4 런타임: NVIDIA 배포 조건 적용. 모델과 실행 엔진을 공식 출처에서 별도 다운로드합니다.\n'
    'https://huggingface.co/naksyu/lime_Q6_K\n'
    'https://github.com/ggml-org/llama.cpp/releases/tag/b11721\n'
    'https://docs.nvidia.com/cuda/eula/index.html'
)


def approved_url(url):
    parts = urlsplit(url)
    host = (parts.hostname or '').lower()
    allowed = ('huggingface.co', 'hf.co', 'github.com', 'githubusercontent.com')
    if (parts.scheme != 'https' or parts.username or parts.password or
        parts.port not in (None, 443) or not any(host == x or host.endswith('.'+x) for x in allowed)):
        raise ValueError('Unapproved download endpoint')
    return url


def file_hash(path, cancelled=None):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            if cancelled and cancelled.is_set():
                raise InterruptedError('Provisioning cancelled')
            digest.update(block)
    return digest.hexdigest()


class LimeInstall:
    def __init__(self, root, *, progress=None):
        self.root = private_path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.progress = progress or (lambda value: None)
        self.cancelled = threading.Event()
        self.state = dict(stage='not_installed', done=0, total=MODEL.size, error=None)
        self.lock = asyncio.Lock()

    def update(self, stage, **values):
        self.state = dict(self.state, stage=stage, **values)
        self.progress(dict(self.state))

    async def blocking(self, function, *args):
        # Cancelling an asyncio Future does not stop its worker thread. Keep
        # ownership until the cooperative file/hash/extract operation exits.
        task = asyncio.create_task(asyncio.to_thread(function, *args))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            self.cancelled.set()
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not task.cancelled():
                task.exception()
            raise

    async def checked(self, path, asset):
        if not path.is_file() or path.is_symlink() or path.stat().st_size != asset.size:
            return False
        return await self.blocking(file_hash, path, self.cancelled) == asset.sha256

    async def download(self, session, asset):
        """Resume only a verified byte range; never append a full 200 response."""
        target = self.root / asset.name
        part = target.with_name(target.name+'.part')
        if any(p.is_symlink() for p in (target, part)):
            raise ValueError('Linked install target')
        if target.exists():
            if await self.checked(target, asset):
                return target
            raise ValueError('Existing file is corrupt; preserve it and select a fresh install folder')
        start = part.stat().st_size if part.exists() else 0
        if start > asset.size:
            raise ValueError('Partial file exceeds pinned size')
        if shutil.disk_usage(self.root).free < asset.size-start+2*1024**3:
            raise OSError('Insufficient disk reserve')
        if start < asset.size:
            url = asset.url
            for redirects in range(6):
                approved_url(url)
                headers = {'Accept-Encoding': 'identity'}
                if start:
                    headers['Range'] = f'bytes={start}-'
                async with session.get(url, headers=headers, allow_redirects=False) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        if redirects == 5:
                            raise ValueError('Too many download redirects')
                        from urllib.parse import urljoin
                        url = urljoin(url, response.headers.get('Location', ''))
                        continue
                    if response.status not in (200, 206):
                        raise RuntimeError(f'Download HTTP {response.status}')
                    if response.headers.get('Content-Encoding', 'identity') != 'identity':
                        raise ValueError('Encoded download is not byte resumable')
                    if response.status == 206:
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                        if not match or tuple(map(int, match.groups())) != (start, asset.size-1, asset.size):
                            raise ValueError('Unexpected download range')
                        mode = 'ab'
                    else:
                        start = 0
                        mode = 'wb'
                    self.update('downloading', file=asset.name, done=start, total=asset.size, error=None)
                    with part.open(mode) as stream:
                        async for block in response.content.iter_chunked(1024**2):
                            if self.cancelled.is_set():
                                raise asyncio.CancelledError()
                            if start+len(block) > asset.size:
                                raise ValueError('Download exceeds pinned size')
                            stream.write(block)
                            start += len(block)
                            self.update('downloading', done=start)
                        stream.flush()
                        os.fsync(stream.fileno())
                    break
        self.update('verifying', file=asset.name, done=start, total=asset.size)
        if not await self.checked(part, asset):
            raise ValueError('Pinned file hash mismatch; partial file preserved')
        if self.cancelled.is_set():
            raise asyncio.CancelledError()
        # The controller owns the process serving lease; within it one install
        # operation owns this directory. Never replace an existing model.
        if target.exists():
            raise FileExistsError('Install destination appeared')
        os.rename(part, target)
        return target

    def extract_engine(self, archives):
        destination = self.root / 'engine-b11721'
        staging = self.root / 'engine-b11721.installing'
        if destination.exists():
            raise FileExistsError('Engine already exists; verification required')
        if staging.exists():
            raise FileExistsError('Interrupted engine extraction; preserve it and use a fresh folder')
        expanded = 0
        for archive in archives:
            with zipfile.ZipFile(archive) as source:
                expanded += sum(x.file_size for x in source.infolist())
        if expanded > 4*1024**3 or shutil.disk_usage(self.root).free < expanded+2*1024**3:
            raise OSError('Engine extraction disk reserve')
        staging.mkdir()
        seen = {}
        total = 0
        try:
            for archive in archives:
                with zipfile.ZipFile(archive) as source:
                    for entry in source.infolist():
                        if self.cancelled.is_set():
                            raise InterruptedError('Provisioning cancelled')
                        name = PurePosixPath(entry.filename)
                        if (not name.parts or name.is_absolute() or '\\' in entry.filename or ':' in entry.filename or
                            '..' in name.parts or stat.S_ISLNK(entry.external_attr >> 16) or
                            any(p.rstrip('. ') != p or p.split('.')[0].upper() in
                                {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
                                for p in name.parts)):
                            raise ValueError('Unsafe engine archive member')
                        if entry.is_dir():
                            continue
                        total += entry.file_size
                        if total > 4*1024**3:
                            raise ValueError('Engine archive expansion limit')
                        path = staging.joinpath(*name.parts)
                        key = str(name).casefold()
                        if key in seen:
                            raise ValueError('Duplicate engine archive member')
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with source.open(entry) as inp, path.open('xb') as out:
                            for block in iter(lambda: inp.read(1024**2), b''):
                                if self.cancelled.is_set():
                                    raise InterruptedError('Provisioning cancelled')
                                out.write(block)
                        seen[key] = True
            servers = list(staging.rglob('llama-server.exe'))
            if len(servers) != 1 or file_hash(servers[0], self.cancelled) != ENGINE_SHA256:
                raise ValueError('Pinned engine executable mismatch')
            # Verify every installed engine byte at subsequent verification.
            records = {p.relative_to(staging).as_posix(): file_hash(p, self.cancelled)
                       for p in staging.rglob('*') if p.is_file()}
            atomic_private_json(staging/'files.json', records)
            os.rename(staging, destination)
            return destination / servers[0].relative_to(staging)
        except BaseException:
            # Only the fresh directory created by this invocation is removed.
            shutil.rmtree(staging)
            raise

    async def verify(self):
        import json
        model = self.root / MODEL.name
        engine = self.root / 'engine-b11721'
        self.update('verifying', error=None)
        if not await self.checked(model, MODEL):
            raise ValueError('Lime file missing or hash mismatch')
        for base, dirs, files in os.walk(engine, followlinks=False):
            for path in [Path(base), *[Path(base)/n for n in (*dirs, *files)]]:
                attributes = path.lstat()
                if stat.S_ISLNK(attributes.st_mode) or getattr(attributes, 'st_file_attributes', 0) & 0x400:
                    raise ValueError('Linked engine file or directory')
        manifest = engine/'files.json'
        if manifest.stat().st_size > 1024**2:
            raise ValueError('Engine file manifest too large')
        records = json.loads(manifest.read_text('utf-8'))
        if not isinstance(records, dict) or not records or len(records) > 500:
            raise ValueError('Invalid engine file manifest')
        actual = {p.relative_to(engine).as_posix() for p in engine.rglob('*') if p.is_file()}
        if actual != set(records) | {'files.json'}:
            raise ValueError('Unexpected engine files')
        for name, digest in records.items():
            path = engine/name
            if (not path.resolve().is_relative_to(engine.resolve()) or path.is_symlink() or
                not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest) or
                await self.blocking(file_hash, path, self.cancelled) != digest):
                raise ValueError('Engine file mismatch')
        servers = list(engine.rglob('llama-server.exe'))
        if len(servers) != 1 or await self.blocking(file_hash, servers[0], self.cancelled) != ENGINE_SHA256:
            raise ValueError('Pinned engine executable mismatch')
        self.update('installed', file=MODEL.name, done=MODEL.size, total=MODEL.size)
        return servers[0], model

    async def repair(self, *, confirmed=False):
        """Explicit, bounded quarantine of this install's damaged artifacts."""
        if not confirmed:
            raise PermissionError('Explicit repair confirmation required')
        if self.lock.locked():
            raise RuntimeError('Install operation already running')
        async with self.lock:
            self.cancelled.clear()
            candidates=[]
            for asset in (MODEL, ENGINE, CUDA):
                path=self.root/asset.name
                if path.exists() and not await self.checked(path,asset):
                    candidates.append(path)
                part=path.with_name(path.name+'.part')
                if part.exists():
                    candidates.append(part)
            candidates.extend(p for p in (self.root/'engine-b11721',self.root/'engine-b11721.installing') if p.exists())
            # Validate every target before moving anything. Only bounded files
            # in this owned installation are quarantined; imported originals
            # and other model directories are never modified.
            moves=[]
            for path in candidates:
                target=path.with_name(path.name+'.rejected')
                if (not path.resolve().is_relative_to(self.root) or target.exists() or target.is_symlink() or path.is_symlink() or
                    getattr(path.lstat(),'st_file_attributes',0)&0x400):
                    raise ValueError('Repair target requires manual backup')
                moves.append((path,target))
            moved=[]
            try:
                for path,target in moves:
                    os.rename(path,target);moved.append((path,target))
            except BaseException:
                for path,target in reversed(moved):
                    if path.exists() or path.is_symlink():
                        raise RuntimeError('Repair rollback requires manual recovery')
                    os.rename(target,path)
                raise
            self.update('not_installed', error=None, done=0)

    async def install(self, *, accepted=False):
        if not accepted:
            raise PermissionError('Explicit model and runtime license review required')
        if self.lock.locked():
            raise RuntimeError('Install operation already running')
        async with self.lock:
            self.cancelled.clear()
            try:
                async with aiohttp.ClientSession(trust_env=False,
                        timeout=aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=60)) as session:
                    await self.download(session, MODEL)
                    if not (self.root/'engine-b11721').exists():
                        archives = [await self.download(session, asset) for asset in (ENGINE, CUDA)]
                        self.update('extracting')
                        await self.blocking(self.extract_engine, archives)
                return await self.verify()
            except (asyncio.CancelledError, InterruptedError):
                self.cancelled.set()
                self.update('cancelled')
                raise
            except Exception as exc:
                self.update('failed', error=type(exc).__name__)
                raise

    def copy_asset(self, source, asset):
        source = private_path(source)
        target = self.root/asset.name
        part = target.with_name(target.name+'.part')
        if source.is_symlink() or source.stat().st_size != asset.size or file_hash(source, self.cancelled) != asset.sha256:
            raise ValueError('Imported source hash mismatch')
        if target.exists():
            if target.is_symlink() or target.stat().st_size != asset.size or file_hash(target, self.cancelled) != asset.sha256:
                raise ValueError('Existing install file preserved')
            return target
        if shutil.disk_usage(self.root).free < asset.size+2*1024**3:
            raise OSError('Import disk reserve')
        with source.open('rb') as inp, part.open('xb') as out:
            for block in iter(lambda: inp.read(1024**2), b''):
                if self.cancelled.is_set():
                    raise InterruptedError('Provisioning cancelled')
                out.write(block)
            out.flush()
            os.fsync(out.fileno())
        if file_hash(part, self.cancelled) != asset.sha256:
            raise ValueError('Imported copy hash mismatch')
        if target.exists():
            raise FileExistsError('Install destination appeared')
        os.rename(part, target)
        return target

    async def import_files(self, model, engine, cuda, *, accepted=False):
        """Copy verified sources without moving/editing existing user weights."""
        if not accepted:
            raise PermissionError('Explicit model and runtime license review required')
        if self.lock.locked():
            raise RuntimeError('Install operation already running')
        async with self.lock:
            self.cancelled.clear()
            try:
                archives = []
                for source, asset in ((model, MODEL), (engine, ENGINE), (cuda, CUDA)):
                    self.update('importing', file=asset.name, error=None)
                    value = await self.blocking(self.copy_asset, source, asset)
                    if asset is not MODEL:
                        archives.append(value)
                if not (self.root/'engine-b11721').exists():
                    self.update('extracting')
                    await self.blocking(self.extract_engine, archives)
                return await self.verify()
            except (asyncio.CancelledError, InterruptedError):
                self.cancelled.set()
                self.update('cancelled')
                raise
            except Exception as exc:
                self.update('failed', error=type(exc).__name__)
                raise
