"""Official Bot Token transport; Discord UI only manages the caller's consent."""
from __future__ import annotations
import asyncio
import json
import re
import time
from .telemetry import measure

import discord
from discord import app_commands

from .actions import Kind
from .runtime import Event,Runtime
from .settings import ROOT,scope
from .vision import VisualCache,download,validate_url


def assets_from_message(message):
    assets=[]
    for a in message.attachments:
        if a.size<=8*1024**2:
            assets.append(("attachment:"+str(a.id),str(a.url)))
    for sticker in message.stickers:
        if sticker.format in (discord.StickerFormatType.png,discord.StickerFormatType.apng,discord.StickerFormatType.gif):
            assets.append(("sticker:"+str(sticker.id),str(sticker.url)))
    for _,asset_id in re.findall(r"<(a?):[A-Za-z0-9_]+:(\d+)>",message.content):
        emoji=next((e for e in message.guild.emojis if e.id==int(asset_id)),None)
        if emoji:assets.append(("emoji:"+str(emoji.id),str(emoji.url)))
    for embed in message.embeds:
        for field in (embed.image,embed.thumbnail):
            if field and field.proxy_url:
                try:validate_url(field.proxy_url)
                except ValueError:continue
                assets.append(("embed:"+str(message.id)+":"+str(len(assets)),field.proxy_url))
    result=[]
    for asset,url in assets:
        try:validate_url(url)
        except ValueError:continue
        if (asset,url) not in result:result.append((asset,url))
    return tuple(result[:4])


class DiscordTransport:
    def ready(self):return self.client.is_ready()

    def address_names(self,event):
        from .naming import validate_name
        guild=self.client.get_guild(event.guild);me=guild.me if guild else None
        names=[]
        for value in (getattr(me,'nick',None),getattr(self.client.user,'global_name',None),getattr(self.client.user,'name',None)):
            try:names.append(validate_name(value))
            except ValueError:pass
        return names

    def other_names(self,event):
        return self.client.runtime.members.names(event.guild,event.channel,self.bot_id)

    async def member_lookup(self,event,users):
        guild=self.client.get_guild(event.guild);channel=guild.get_channel_or_thread(event.channel) if guild else None
        if not channel:return ()
        rows=[]
        for uid in users[:4]:
            try:member=guild.get_member(uid) or await asyncio.wait_for(guild.fetch_member(uid),2)
            except discord.NotFound:
                self.client.runtime.members.clear(event.guild,user=uid)
                await asyncio.to_thread(self.client.companion.clear_aliases,event.guild,uid)
                continue
            except (discord.HTTPException,asyncio.TimeoutError):
                self.client.runtime.note('member_lookup_unavailable');continue
            if member.bot or not channel.permissions_for(member).view_channel:continue
            if isinstance(channel,discord.Thread) and channel.type==discord.ChannelType.private_thread and not channel.get_member(uid) and not member.guild_permissions.manage_threads:continue
            names=tuple(dict.fromkeys(n for n in (member.nick,member.display_name,member.global_name,member.name) if n))
            rows.append((uid,names));self.client.user_names[(event.guild,uid)]=member.display_name[:80]
        return rows

    async def deliver_reminder(self,row,fresh):
        if not self.client.is_ready():raise ValueError('Disconnected')
        channel=await self.client.fetch_channel(int(row['channel']))
        if not getattr(channel,'guild',None) or channel.guild.id!=int(row['guild']):raise ValueError('Wrong guild')
        if not isinstance(channel,(discord.TextChannel,discord.Thread)):raise ValueError('Unsupported destination')
        if isinstance(channel,discord.Thread) and (channel.archived or channel.locked):raise ValueError('Thread unavailable')
        if row['target']!=row['requester']:raise ValueError('Target must be requester')
        target=await channel.guild.fetch_member(int(row['target']))
        if target.bot or not await fresh():raise ValueError('Stale reminder')
        mention=discord.AllowedMentions(everyone=False,roles=False,users=[discord.Object(id=target.id)],replied_user=False)
        sent=await channel.send(f"<@{target.id}> 예약한 시간이야. 부탁한 내용: {row['text'][:300]}",
                                nonce=row['reminder_id'],allowed_mentions=mention,suppress_embeds=True)
        return sent.id

    def __init__(self,client):self.client=client
    @property
    def bot_id(self):return self.client.user.id
    def channel(self,event):
        guild=self.client.get_guild(event.guild)
        return guild.get_channel_or_thread(event.channel) if guild else None
    async def verify_adult(self,event):
        channel=self.channel(event)
        if not channel:return False
        target=channel.parent if isinstance(channel,discord.Thread) else channel
        if not target:return False
        # Refresh the actual channel age gate immediately before adult output,
        # rather than trusting a possibly delayed Gateway channel-update event.
        latest=await self.client.fetch_channel(target.id)
        return bool(getattr(latest,'guild',None) and latest.guild.id==event.guild and
                    isinstance(latest,(discord.TextChannel,discord.ForumChannel)) and latest.is_nsfw())
    async def indicate_typing(self,event,fresh):
        try:
            while await fresh():
                channel=self.channel(event)
                if not channel:return
                await channel.typing()
                await asyncio.sleep(6)
        except discord.HTTPException:return
    async def permissions(self,event):
        with measure("permissions"):return await self._permissions(event)
    async def _permissions(self,event,force=False):
        channel=self.channel(event)
        if not channel or not channel.guild.me:return {}
        if isinstance(channel,discord.Thread) and (channel.archived or channel.locked):return {}
        # Re-read our membership so role removal is detected without Members Intent.
        cached=getattr(self.client,'bot_members',{}).get(channel.guild.id)
        if not force and cached and time.monotonic()-cached[0]<5:member=cached[1]
        else:
            member=await channel.guild.fetch_member(self.bot_id)
            if not hasattr(self.client,'bot_members'):self.client.bot_members={}
            self.client.bot_members[channel.guild.id]=(time.monotonic(),member)
        p=channel.permissions_for(member)
        return dict(view=p.view_channel,send=(p.send_messages_in_threads if isinstance(channel,discord.Thread) else p.send_messages),
                    react=p.add_reactions and p.read_message_history,attach=p.attach_files,
                    age_restricted=bool((channel.parent if isinstance(channel,discord.Thread) else channel) and
                        (channel.parent if isinstance(channel,discord.Thread) else channel).is_nsfw()))
    async def catalog(self,event,cache):
        with measure("catalog"):return await self._catalog(event,cache)
    async def _catalog(self,event,cache):
        channel=self.channel(event)
        if not channel:return dict(reactions={},stickers={})
        reactions={"🙂":"가벼운 동의", "🎉":"축하", "👍":"동의", "😮":"놀람"}
        from .reaction_requests import requested_reaction
        requested=requested_reaction(event.content)
        if requested:reactions[requested[0]]='사용자가 명시한 Unicode 반응'
        return dict(reactions=reactions,stickers={})
    async def execute(self,event,action,library,fresh):
        with measure("discord_send"):return await self._execute(event,action,library,fresh)
    async def _execute(self,event,action,library,fresh):
        if action.kind in {Kind.MEDIA,Kind.TEXT_MEDIA,Kind.STICKER}:raise ValueError('Media and sticker output removed')
        if action.kind in {Kind.REACTION,Kind.TEXT_REACTION} and '<' in action.asset:raise ValueError('Custom emoji disabled')
        permissions=await self._permissions(event,force=True)
        if not permissions.get('view') or action.kind in (Kind.TEXT,Kind.TEXT_REACTION) and not permissions.get('send') or action.kind in (Kind.REACTION,Kind.TEXT_REACTION) and not permissions.get('react'):raise PermissionError('Output permission changed')
        channel=self.channel(event)
        if not channel or not await fresh():raise ValueError("Stale output")
        current=await channel.fetch_message(event.response_to or event.id)
        verified_sources={event.response_to or event.id:current}
        if event.target_content_hash:
            import hashlib
            if hashlib.sha256(current.content.encode()).hexdigest()!=event.target_content_hash:raise ValueError('Original message changed')
            if event.response_to and event.response_to!=event.id and event.source_content_hash:
                latest=await channel.fetch_message(event.id)
                verified_sources[event.id]=latest
                if hashlib.sha256(latest.content.encode()).hexdigest()!=event.source_content_hash:raise ValueError('Supplement changed')
        for part in event.raw_parts:
            source=verified_sources.get(part.id)
            if source is None:
                source=await channel.fetch_message(part.id)
                verified_sources[part.id]=source
            if (source.author.id!=part.author or source.channel.id!=part.channel or source.content!=part.content):
                raise ValueError('Utterance source changed')
        if not await fresh():raise ValueError("Stale output")
        sent=None
        if action.kind in {Kind.TEXT,Kind.TEXT_REACTION}:
            kwargs=dict(content=action.text,allowed_mentions=discord.AllowedMentions.none(),mention_author=False,nonce=event.response_to or event.id,suppress_embeds=True)
            sent=await current.reply(**kwargs)
        if action.kind in {Kind.REACTION,Kind.TEXT_REACTION}:
            if not await fresh():raise ValueError("Stale reaction")
            if action.target:
                if action.target not in {event.id,event.response_to,event.reply_to,event.reaction_target}:raise ValueError('Unverified reaction target')
                if action.target!=current.id:
                    current=verified_sources.get(action.target)
                    if current is None:current=await channel.fetch_message(action.target)
                if event.reaction_target_hash:
                    import hashlib
                    if hashlib.sha256(current.content.encode()).hexdigest()!=event.reaction_target_hash:raise ValueError('Reaction target changed')
            if not await fresh():raise ValueError('Stale reaction target')
            if any(r.me and str(r.emoji)==action.asset for r in current.reactions):return sent.id if sent else None
            await current.add_reaction(action.asset)
        return sent.id if sent else None


class EchoClient(discord.Client):
    def __init__(self,settings,backend,admin_guilds):
        intents=discord.Intents.none();intents.guilds=True;intents.guild_messages=True
        intents.message_content=True;intents.emojis_and_stickers=True;intents.guild_reactions=True
        super().__init__(intents=intents,allowed_mentions=discord.AllowedMentions.none(),max_messages=None,
                         member_cache_flags=discord.MemberCacheFlags.none())
        self.settings=settings;self.backend=backend;self.admin_guilds=admin_guilds
        self.tree=app_commands.CommandTree(self);self.cache=VisualCache(settings.path.parent/'visual.sqlite3');self.library=None
        self.user_names={}
        from .companion_store import CompanionStore
        self.companion=CompanionStore(settings.path.parent/'companion.sqlite3')
        self.runtime=Runtime(settings,backend,DiscordTransport(self),self.cache,self.library,
                             ledger_path=settings.path.parent/'sent.sqlite3',companion=self.companion)
        self.runtime.gateway_available=False
        self.owner_tasks=set()
        self.shutdown_lock=asyncio.Lock()
        self.install_commands()

    def install_commands(self):
        from .consent_ui import open_consent
        @app_commands.guild_only()
        async def consent(i:discord.Interaction):await open_consent(self,i)
        self.tree.add_command(app_commands.Command(name='동의',description='내 친밀도·기억·대화 요약의 저장 동의와 삭제',callback=consent))
        @self.tree.error
        async def command_error(i,error):
            self.runtime.note('consent_command_failed')
            if not i.response.is_done():await i.response.send_message('저장소 처리에 실패했어. 변경 완료로 간주하지 말고 다시 확인해 줘.',ephemeral=True)
            else:await i.followup.send('처리를 완료하지 못했어. 다시 확인해 줘.',ephemeral=True)

    async def setup_hook(self):
        # Never reconcile commands without explicit local-owner approval.
        if not self.settings.get()['command_sync_pending']:return
        before=await self.tree.fetch_commands()
        audit=dict(global_before=[c.name for c in before],guilds={})
        await self.tree.sync()
        for guild in sorted(set(self.admin_guilds)|{int(g) for g in self.settings.get()['guilds']}):
            target=discord.Object(guild);self.tree.clear_commands(guild=target)
            audit['guilds'][str(guild)]=[c.name for c in await self.tree.fetch_commands(guild=target)]
            await self.tree.sync(guild=target)
        from .settings import atomic_private_json
        atomic_private_json(self.settings.path.parent/'command-audit.json',audit)
        self.settings.set(self.settings.owner_id,'command_sync_pending',False)
        self.runtime.note('consent_commands_reconciled')

    async def apply_guild_name(self,guild_id):
        from .naming import guild_name
        if not hasattr(self,'name_lock'):self.name_lock=asyncio.Lock()
        async with self.name_lock:
            guild=self.get_guild(guild_id)
            if not guild or not guild.me:return
            name=guild_name(self.settings.get(),guild_id)
            if guild.me.nick==name:return
            try:await guild.me.edit(nick=name,reason='Owner configured bot name')
            except discord.HTTPException as exc:
                self.runtime.note('nickname_update_failed_'+type(exc).__name__)
                raise

    async def on_ready(self):
        await self.runtime.resume_gateway()
        self.runtime.start_services()
        self.runtime.note("gateway_ready")
        for gid,g in self.settings.get()['guilds'].items():
            if 'name' in g:
                try:await self.apply_guild_name(int(gid))
                except discord.HTTPException:pass
    async def on_disconnect(self):self.runtime.pause_gateway();self.runtime.note("gateway_disconnected")
    async def on_resumed(self):await self.runtime.resume_gateway();self.runtime.note("gateway_resumed")
    async def on_error(self,event,*args,**kwargs):self.runtime.note("gateway_event_failed")

    async def on_message(self,message):
        received=time.monotonic()
        if not message.guild or message.author.bot or message.webhook_id:return
        self.runtime.note('gateway_message_received')
        parent=message.channel.parent_id if isinstance(message.channel,discord.Thread) else None
        cfg=self.settings.get()
        if scope(cfg,message.guild.id,message.channel.id,parent)=="silent":self.runtime.note('scope_denied');return
        self.user_names[(message.guild.id,message.author.id)]=message.author.display_name[:80]
        if len(self.user_names)>1000:self.user_names.pop(next(iter(self.user_names)))
        await self.runtime.ingest(Event(message.id,message.guild.id,message.channel.id,message.author.id,
            message.content,message.created_at,parent=parent,reply_to=message.reference.message_id if message.reference else None,
            assets=assets_from_message(message) if cfg['vision'] else (),received_at=received,
            member_names=tuple((u.id,tuple(dict.fromkeys(n for n in (getattr(u,'nick',None),u.display_name,getattr(u,'global_name',None),u.name) if n))) for u in (message.author,*message.mentions) if not u.bot),
            member_mentions=tuple(u.id for u in message.mentions),
            reply_author=(target.author.id if message.reference and isinstance((target:=message.reference.resolved),discord.Message) and target.channel.id==message.channel.id and target.guild and target.guild.id==message.guild.id else None)))

    async def on_raw_message_delete(self,payload):
        if payload.guild_id:await self.runtime.message_changed(payload.guild_id,payload.channel_id,payload.message_id)
    async def on_raw_message_edit(self,payload):
        if payload.guild_id and 'content' in payload.data:await self.runtime.message_changed(payload.guild_id,payload.channel_id,payload.message_id,payload.data['content'])
    async def _reaction_event(self,payload,remove):
        if not payload.guild_id or payload.user_id==self.user.id:return
        guild=self.get_guild(payload.guild_id)
        if not guild:return
        channel=guild.get_channel_or_thread(payload.channel_id)
        parent=channel.parent_id if isinstance(channel,discord.Thread) else None
        if scope(self.settings.get(),guild.id,payload.channel_id,parent)=='silent':return
        try:member=getattr(payload,'member',None) or await guild.fetch_member(payload.user_id)
        except discord.HTTPException:return
        if not member.bot:await self.runtime.reaction_event(guild.id,payload.channel_id,member.id,payload.message_id,str(payload.emoji),remove=remove,parent=parent)
    async def on_raw_reaction_add(self,payload):await self._reaction_event(payload,False)
    async def on_raw_reaction_remove(self,payload):await self._reaction_event(payload,True)
    async def on_guild_channel_update(self,before,after):self.runtime.invalidate(after.id);self.runtime.members.clear(after.guild.id,channel=after.id)
    async def on_guild_channel_delete(self,channel):
        self.runtime.invalidate(channel.id);self.runtime.members.clear(channel.guild.id,channel=channel.id)
        await asyncio.to_thread(self.companion.clear_aliases,channel.guild.id,channel=channel.id)
    async def on_guild_role_update(self,before,after):self.runtime.invalidate_guild(after.guild.id);self.runtime.members.clear(after.guild.id)
    async def on_guild_role_delete(self,role):self.runtime.invalidate_guild(role.guild.id);self.runtime.members.clear(role.guild.id)
    async def on_thread_update(self,before,after):self.runtime.invalidate(after.id);self.runtime.members.clear(after.guild.id,channel=after.id)
    async def on_thread_delete(self,thread):
        self.runtime.invalidate(thread.id);self.runtime.members.clear(thread.guild.id,channel=thread.id)
        await asyncio.to_thread(self.companion.clear_aliases,thread.guild.id,channel=thread.id)
    async def on_raw_thread_delete(self,payload):
        self.runtime.invalidate(payload.thread_id);self.runtime.members.clear(payload.guild_id,channel=payload.thread_id)
        await asyncio.to_thread(self.companion.clear_aliases,payload.guild_id,channel=payload.thread_id)
    async def on_member_update(self,before,after):
        if self.user and after.id==self.user.id:getattr(self,'bot_members',{}).pop(after.guild.id,None)
        # Events available without bulk member fetching. MESSAGE_CREATE refreshes
        # observed members even when Discord does not send this privileged event.
        keys=[k for k in self.runtime.members.people if k[0]==after.guild.id and k[2]==after.id]
        for _,channel,_ in keys:self.runtime.members.observe(after.guild.id,channel,after.id,(after.display_name,after.name))
        self.user_names[(after.guild.id,after.id)]=after.display_name[:80]
    async def on_member_remove(self,member):
        self.runtime.members.clear(member.guild.id,user=member.id);self.user_names.pop((member.guild.id,member.id),None)
        await asyncio.to_thread(self.companion.clear_aliases,member.guild.id,member.id)
    async def on_guild_remove(self,guild):
        self.runtime.invalidate_guild(guild.id);self.cache.clear(guild.id);self.runtime.members.clear(guild.id)
        self.user_names={k:v for k,v in self.user_names.items() if k[0]!=guild.id}
        await asyncio.to_thread(self.companion.clear_aliases,guild.id)
    async def on_guild_emojis_update(self,guild,before,after):
        self.cache.retain(guild.id,set(),"emoji:");self.runtime.invalidate_guild(guild.id)
    async def on_guild_stickers_update(self,guild,before,after):
        self.cache.retain(guild.id,set(),"sticker:")
        if self.settings.get()["vision"]:self.runtime.invalidate_guild(guild.id)

    async def close(self):
        async with self.shutdown_lock:
            if self.is_closed():return
            tasks=[task for task in self.owner_tasks if task is not asyncio.current_task()]
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            try:await self.runtime.close()
            finally:await super().close()
