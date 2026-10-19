"""Owner identity is bootstrap-only; mutable settings are authenticated at rest."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import time

ROOT = Path(__file__).resolve().parents[2] / "local_data" / "bot"
MODES = {"silent", "mention", "autonomous", "reaction"}
MOODS = {"평온", "기쁨", "신남", "우울", "화남", "피곤함", "부끄러움"}
ACTIVITY = {"quiet": .05, "normal": .2, "active": .45, "very_active": .7}
GENDERS={'female','male','neutral'}
MODELS={'base','persona','adult'}
DEFAULTS = dict(enabled=False, text=True, reactions=False, stickers=False, media=False,
                vision=False, mood="평온", warmth=75, cuteness=40, playfulness=20,
                auto_mood=False, activity="normal", cooldown=60, engagement_seconds=600,
                media_probability=0., model="persona", guilds={},asset_policy=3,gender='neutral',
                memory_auto=False,relations_auto=True,context_excerpts=True,reminders_enabled=True,reminder_grace=900,
                memory_plan_grace=3600,memory_date_grace=86400,memory_state_hours=6,
                command_sync_pending=False,web_search=False,summaries_auto=False)


def private_path(value):
    p = Path(value).resolve()
    if not p.is_relative_to(ROOT.parent.resolve()):
        raise ValueError("Private files must remain in local_data")
    return p


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def atomic_private_json(path,value):
    """Retry transient Windows sharing/AV locks; keep old file on failure."""
    temporary=path.with_name(path.name+'.'+secrets.token_hex(4)+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        for attempt in range(5):
            try:temporary.replace(path);break
            except PermissionError:
                if attempt==4:raise
                time.sleep(.02*(2**attempt))
    finally:
        temporary.unlink(missing_ok=True)


def positive_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError("A positive Discord ID is required")
    return value


def validate(cfg):
    if set(cfg) != set(DEFAULTS):
        raise ValueError("Unknown settings; owner identity cannot be configured here")
    if cfg['asset_policy']!=3 or cfg['media'] or cfg['media_probability']!=0 or cfg['stickers']:raise ValueError('Media and sticker output removed')
    for key in ("enabled", "text", "reactions", "stickers", "media", "vision", "auto_mood",'memory_auto','relations_auto','context_excerpts','reminders_enabled','command_sync_pending','web_search','summaries_auto'):
        if type(cfg[key]) is not bool:
            raise ValueError("Boolean required")
    if cfg["mood"] not in MOODS or cfg["activity"] not in ACTIVITY or cfg["model"] not in MODELS or cfg['gender'] not in GENDERS:
        raise ValueError("Unknown mood, activity or trusted model")
    for key, lo, hi in (("warmth", 0, 100), ("cuteness", 0, 100), ("playfulness", 0, 100),
                        ("cooldown", 2, 3600), ("engagement_seconds", 10, 86400),('reminder_grace',0,86400),('memory_plan_grace',0,86400),('memory_date_grace',0,86400),('memory_state_hours',1,72)):
        if type(cfg[key]) is not int or not lo <= cfg[key] <= hi:
            raise ValueError("Setting outside permitted range")
    if type(cfg["media_probability"]) not in (int, float) or not 0 <= cfg["media_probability"] <= 1:
        raise ValueError("Media probability must be 0..1")
    if not isinstance(cfg["guilds"], dict) or len(cfg["guilds"]) > 20:
        raise ValueError("Guild limit")
    for gid, g in cfg["guilds"].items():
        positive_id(int(gid))
        if not {'enabled','channels','threads'}<=set(g) or set(g)-{'enabled','channels','threads','name','aliases','partial_names','timezone'} or type(g["enabled"]) is not bool:
            raise ValueError("Invalid guild")
        if 'name' in g:
            from .naming import validate_name
            validate_name(g['name'])
        if 'timezone' in g:
            from .temporal import zone
            zone(g['timezone'])
        if 'partial_names' in g and type(g['partial_names']) is not bool:raise ValueError('Invalid name matching')
        if 'aliases' in g:
            from .naming import validate_name
            if not isinstance(g['aliases'],list) or len(g['aliases'])>8:raise ValueError('Alias limit')
            for alias in g['aliases']:validate_name(alias)
        if len(g["channels"]) + len(g["threads"]) > 200:
            raise ValueError("Scope limit")
        for table, rules in (("channels", g["channels"]), ("threads", g["threads"])):
            for cid, rule in rules.items():
                positive_id(int(cid))
                if set(rule) not in ({"mode", "inherit"},{"mode", "inherit","reaction_mode"}) or rule["mode"] not in MODES or type(rule["inherit"]) is not bool:
                    raise ValueError("Invalid scope")
                if rule.get('reaction_mode','mention') not in {'silent','mention','autonomous'}:raise ValueError('Invalid reaction scope')
                if table == "threads" and rule["inherit"]:
                    raise ValueError("Only a parent channel can grant inheritance")
    return cfg


def scope(cfg, guild_id, channel_id, parent_id=None, *, action=None):
    if not cfg["enabled"]:
        return "silent"
    g = cfg["guilds"].get(str(guild_id))
    if not g or not g["enabled"]:
        return "silent"
    if parent_id is not None:
        rule = g["threads"].get(str(channel_id))
        if not rule:
            parent = g["channels"].get(str(parent_id))
            rule=parent if parent and parent['inherit'] else None
    else:rule=g['channels'].get(str(channel_id))
    if not rule:return 'silent'
    mode=rule['mode']
    # Legacy scopes retain their exact behavior until explicitly separated.
    if 'reaction_mode' not in rule:
        return ('silent' if mode=='reaction' else mode) if action=='text' else mode
    reaction=rule['reaction_mode']
    if action=='text':return mode
    if action=='reaction':return reaction
    if mode=='silent':return 'reaction' if reaction!='silent' else 'silent'
    return 'autonomous' if reaction=='autonomous' else mode


class Settings:
    def __init__(self, owner_id, key, path=ROOT / "settings.json"):
        self.owner_id = positive_id(owner_id)
        if not isinstance(key, str) or len(key) < 32:
            raise ValueError("Missing bootstrap signing key")
        self._key = key.encode()
        self.path = private_path(path)
        self.revision = 0
        self._cfg = deepcopy(DEFAULTS)
        if self.path.exists():
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
            actual = hmac.new(self._key, canonical(envelope["data"]), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(actual, envelope["signature"]):
                raise PermissionError("Settings integrity failure; start disabled and repair locally")
            verified=dict(envelope['data'])
            # Authenticate original bytes before dropping the obsolete quota.
            verified.pop('daily_limit',None)
            if 'asset_policy' not in verified:
                # Authenticate first; previous QA vision opt-in must not enable the new experiment.
                verified=dict(verified,asset_policy=2,vision=False,media=False,media_probability=0.)
            if verified['asset_policy'] not in (2,3):raise ValueError('Unsupported asset policy')
            verified=dict(verified,asset_policy=3,stickers=False)
            # Migrate only after verifying the original signature; never auto-enable adult mode.
            if 'gender' not in verified:verified=dict(verified,gender='neutral')
            for key in ('memory_auto','relations_auto','context_excerpts','reminders_enabled','reminder_grace','memory_plan_grace','memory_date_grace','memory_state_hours','command_sync_pending','web_search','summaries_auto'):
                if key not in verified:verified=dict(verified,**{key:deepcopy(DEFAULTS[key])})
            self._cfg = validate(verified)

    def authorize(self, user_id):
        if type(user_id) is not int or user_id != self.owner_id:
            raise PermissionError("Not authorized")

    def get(self):
        return deepcopy(self._cfg)

    def change(self, user_id, mutate):
        self.authorize(user_id)
        updated = self.get()
        mutate(updated)
        validate(updated)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        envelope = dict(data=updated, signature=hmac.new(self._key, canonical(updated), hashlib.sha256).hexdigest())
        atomic_private_json(self.path,envelope)
        self._cfg = updated
        self.revision += 1

    def set(self, user_id, key, value):
        if key in {"guilds","asset_policy","media","media_probability"} or key not in DEFAULTS:
            raise ValueError("Use scope commands")
        self.change(user_id, lambda cfg: cfg.update({key: value}))

    def set_scope(self, user_id, guild_id, channel_id, mode, *, thread=False, inherit=False):
        positive_id(guild_id); positive_id(channel_id)
        def mutate(cfg):
            g = cfg["guilds"].setdefault(str(guild_id), dict(enabled=True, channels={}, threads={}))
            g["threads" if thread else "channels"][str(channel_id)] = dict(mode=mode, inherit=inherit)
        self.change(user_id, mutate)

    def set_activity_scope(self,user_id,guild_id,channel_id,text_mode,reaction_mode,*,thread=False,inherit=False):
        positive_id(guild_id);positive_id(channel_id)
        if text_mode not in {'silent','mention','autonomous'}:raise ValueError('Invalid text scope')
        def mutate(cfg):
            g=cfg['guilds'].setdefault(str(guild_id),dict(enabled=True,channels={},threads={}))
            g['threads' if thread else 'channels'][str(channel_id)]=dict(mode=text_mode,reaction_mode=reaction_mode,inherit=inherit)
        self.change(user_id,mutate)
