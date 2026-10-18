"""Bounded Discord CDN download, sampled frames, guild-isolated visual cache."""
from __future__ import annotations
import asyncio
import hashlib
from io import BytesIO
import ipaddress
import json
import re
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlsplit
import warnings
import weakref

from PIL import Image
from .settings import private_path, ROOT

MAX_BYTES = 8 * 1024**2
MAX_PIXELS = 12_000_000
MAX_FRAMES = 200
ANALYSIS_VERSION = "gemma4-base-frames-v1"


def validate_url(url):
    u = urlsplit(str(url))
    cdn = u.hostname in {"cdn.discordapp.com", "media.discordapp.net"}
    proxy = u.hostname in {"images-ext-1.discordapp.net", "images-ext-2.discordapp.net"}
    path_ok = cdn and u.path.startswith(("/attachments/", "/ephemeral-attachments/", "/emojis/", "/stickers/"))
    path_ok = path_ok or (proxy and u.path.startswith("/external/"))
    if u.scheme != "https" or u.port not in (None, 443) or u.username or u.password or u.fragment or not path_ok:
        raise ValueError("Untrusted Discord asset reference")
    return str(url)


async def download(url, session=None):
    import aiohttp
    from aiohttp.resolver import ThreadedResolver
    validate_url(url)
    class PublicResolver(ThreadedResolver):
        async def resolve(self, *args, **kwargs):
            result = await super().resolve(*args, **kwargs)
            if any(not ipaddress.ip_address(r["host"]).is_global for r in result):
                raise ValueError("Non-public CDN address")
            return result
    if session is None:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(resolver=PublicResolver()),
                                       timeout=aiohttp.ClientTimeout(total=12), trust_env=False,
                                       auto_decompress=False) as own:
            return await download(url, own)
    async with session.get(url, allow_redirects=False) as response:
        if response.status != 200:
            raise ValueError("CDN download failed")
        if response.content_length and response.content_length > MAX_BYTES:
            raise ValueError("Asset too large")
        body = bytearray()
        async for block in response.content.iter_chunked(65536):
            body.extend(block)
            if len(body) > MAX_BYTES:
                raise ValueError("Asset too large")
        return bytes(body)


def frames(data):
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Asset byte limit")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as image:
            if image.format not in {"PNG", "JPEG", "GIF", "WEBP"}:
                raise ValueError("Unsupported raster format; Lottie is not rendered")
            if image.width * image.height > MAX_PIXELS or max(image.size) > 8192:
                raise ValueError("Pixel limit")
            count = getattr(image, "n_frames", 1)
            if count > MAX_FRAMES or image.width*image.height*count>48_000_000:
                raise ValueError("Animation frame limit")
            selected = sorted({round(i * (count-1) / min(3, count-1)) for i in range(min(4, count))}) if count > 1 else [0]
            result = []
            for i in selected:
                image.seek(i)
                frame = image.convert("RGB")
                frame.thumbnail((640, 640))
                result.append(frame.copy())
            return result, dict(format=image.format, frames=count, sampled=selected,
                                uncertainty="Sampled frames cannot prove all motion or hidden details.")


def parse_visual(text):
    fenced=re.fullmatch(r"\s*```(?:json)?\s*\n?([\s\S]*?)\n?```\s*",text)
    if fenced:text=fenced.group(1)
    obj = json.loads(text)
    keys = {"objects", "emotion_candidates", "action", "motion", "uncertainty", "evidence"}
    if not isinstance(obj, dict) or set(obj) != keys:
        raise ValueError("Invalid visual result")
    if any(not isinstance(obj[k], list) or len(obj[k]) > 12 or any(not isinstance(v,str) or len(v)>300 for v in obj[k])
           for k in ("objects", "emotion_candidates", "evidence")):
        raise ValueError("Invalid visual list")
    if any(not isinstance(obj[k], str) or len(obj[k]) > 1000 for k in ("action", "motion", "uncertainty")):
        raise ValueError("Invalid visual description")
    return obj


class VisualCache:
    def __init__(self, path=ROOT / "visual.sqlite3", max_entries=1000):
        self.path = private_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self.locks = weakref.WeakValueDictionary()
        with self.db() as db:
            db.execute("PRAGMA max_page_count=12500")
            db.execute("CREATE TABLE IF NOT EXISTS visual (guild TEXT, asset TEXT, hash TEXT, version TEXT, result TEXT, at REAL, PRIMARY KEY(guild,asset))")

    def db(self):
        return sqlite3.connect(self.path)

    def clear(self, guild, asset=None):
        with self.db() as db:
            if asset is None:
                db.execute("DELETE FROM visual WHERE guild=?", (str(guild),))
            else:
                db.execute("DELETE FROM visual WHERE guild=? AND asset=?", (str(guild), str(asset)))

    def descriptions(self,guild):
        with self.db() as db:
            return {asset:json.loads(result) for asset,result in db.execute(
                "SELECT asset,result FROM visual WHERE guild=? AND version=?",(str(guild),ANALYSIS_VERSION))}

    def retain(self, guild, live_assets, prefix):
        with self.db() as db:
            for (asset,) in db.execute("SELECT asset FROM visual WHERE guild=?", (str(guild),)).fetchall():
                if asset.startswith(prefix) and asset not in live_assets:
                    db.execute("DELETE FROM visual WHERE guild=? AND asset=?", (str(guild),asset))

    async def analyze(self, guild, asset, data, backend, force=False):
        key = (str(guild), str(asset))
        lock = self.locks.setdefault(key, asyncio.Lock())
        async with lock:
            digest = hashlib.sha256(data).hexdigest()
            with self.db() as db:
                found = db.execute("SELECT hash,version,result FROM visual WHERE guild=? AND asset=?",key).fetchone()
            if found and found[:2] == (digest, ANALYSIS_VERSION) and not force:
                return json.loads(found[2])
            sampled, metadata = await asyncio.to_thread(frames, data)
            result = parse_visual(await backend.visual(sampled, metadata))
            result["uncertainty"] += " " + metadata["uncertainty"]
            with self.db() as db:
                db.execute("INSERT OR REPLACE INTO visual VALUES(?,?,?,?,?,?)", (*key,digest,ANALYSIS_VERSION,json.dumps(result,ensure_ascii=False),time.time()))
                db.execute("DELETE FROM visual WHERE rowid IN (SELECT rowid FROM visual ORDER BY at DESC LIMIT -1 OFFSET ?)",(self.max_entries,))
            return result
