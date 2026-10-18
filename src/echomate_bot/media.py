"""Owner-approved outbound copies; inbound cache never grants send permission."""
from __future__ import annotations
import hashlib
import json
import time
import asyncio
from .settings import ROOT, private_path,atomic_private_json
from .vision import frames


class MediaLibrary:
    def __init__(self, settings, root=ROOT / "library"):
        self.settings = settings
        self.root = private_path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        # Approval records live in a separate authenticated store using the same bootstrap trust.
        from .settings import canonical
        self.canonical = canonical
        self.index = self.root / "index.json"
        self.records = self._read()

    def _read(self):
        import hmac
        if not self.index.exists(): return {}
        obj=json.loads(self.index.read_text(encoding="utf-8"))
        sig=hmac.new(self.settings._key,self.canonical(obj["data"]),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,obj["signature"]): raise PermissionError("Media approval integrity failure")
        return obj["data"]

    def save(self):
        import hmac
        sig=hmac.new(self.settings._key,self.canonical(self.records),hashlib.sha256).hexdigest()
        atomic_private_json(self.index,dict(data=self.records,signature=sig))

    async def register(self, user_id, data, guild_id, tags, purpose, cache, backend):
        self.settings.authorize(user_id)
        if len(self.records) >= 100: raise ValueError("Media library limit")
        if sum(p.stat().st_size for p in self.root.iterdir() if p.is_file())+len(data)>128*1024**2:
            raise ValueError("Media library storage limit")
        _, metadata = await asyncio.to_thread(frames,data)
        digest=hashlib.sha256(data).hexdigest()
        mid=digest[:20]
        analysis=await cache.analyze(guild_id,"library:"+mid,data,backend)
        path=self.root/(mid+"."+metadata["format"].lower())
        path.write_bytes(data)
        self.records[mid]=dict(hash=digest,file=path.name,type=metadata["format"],analysis=analysis,
                               tags=tags[:300],purpose=purpose[:300],guilds=[guild_id],enabled=True,
                               cooldown=3600,last_used=0)
        self.save()
        return mid

    def edit(self,user_id,mid,**values):
        self.settings.authorize(user_id)
        if set(values)-{"tags","purpose","enabled","guilds","cooldown"}: raise ValueError("Unsupported media setting")
        if "guilds" in values and any(type(g) is not int or g<=0 for g in values["guilds"]): raise ValueError("Invalid guild")
        if "enabled" in values and type(values["enabled"]) is not bool: raise ValueError("Invalid enabled flag")
        if "cooldown" in values and (type(values["cooldown"]) is not int or not 60<=values["cooldown"]<=86400): raise ValueError("Invalid cooldown")
        for k in ("tags","purpose"):
            if k in values and (not isinstance(values[k],str) or len(values[k])>300): raise ValueError("Invalid metadata")
        self.records[mid].update(values);self.save()

    def resolve(self,mid,guild_id):
        rec=self.records.get(mid)
        if not rec or not rec["enabled"] or guild_id not in rec["guilds"] or time.time()-rec["last_used"]<rec["cooldown"]:
            raise PermissionError("Media not approved or cooling down")
        path=(self.root/rec["file"]).resolve()
        if not path.is_relative_to(self.root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=rec["hash"]:
            raise PermissionError("Approved media changed")
        return path

    def used(self,mid):
        self.records[mid]["last_used"]=time.time();self.save()

    def delete(self,user_id,mid):
        self.settings.authorize(user_id)
        rec=self.records.pop(mid)
        path=(self.root/rec["file"]).resolve()
        if path.is_relative_to(self.root.resolve()): path.unlink(missing_ok=True)
        self.save()
