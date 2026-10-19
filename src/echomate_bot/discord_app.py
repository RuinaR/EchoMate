"""Official Bot Token transport. Commands and components independently authorize owner."""
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
from .settings import ROOT,MOODS,scope
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
    async def _permissions(self,event):
        channel=self.channel(event)
        if not channel or not channel.guild.me:return {}
        if isinstance(channel,discord.Thread) and (channel.archived or channel.locked):return {}
        # Re-read our membership so role removal is detected without Members Intent.
        member=await channel.guild.fetch_member(self.bot_id)
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
        stickers=self.client.standard_catalog(event.content)
        return dict(reactions=reactions,stickers=stickers)
    async def execute(self,event,action,library,fresh):
        with measure("discord_send"):return await self._execute(event,action,library,fresh)
    async def _execute(self,event,action,library,fresh):
        if action.kind in {Kind.MEDIA,Kind.TEXT_MEDIA}:raise ValueError('Media output removed')
        if action.kind in {Kind.REACTION,Kind.TEXT_REACTION} and '<' in action.asset:raise ValueError('Custom emoji disabled')
        channel=self.channel(event)
        if not channel or not await fresh():raise ValueError("Stale output")
        current=await channel.fetch_message(event.response_to or event.id)
        if event.target_content_hash:
            import hashlib
            if hashlib.sha256(current.content.encode()).hexdigest()!=event.target_content_hash:raise ValueError('Original message changed')
            if event.response_to and event.response_to!=event.id and event.source_content_hash:
                latest=await channel.fetch_message(event.id)
                if hashlib.sha256(latest.content.encode()).hexdigest()!=event.source_content_hash:raise ValueError('Supplement changed')
        if not await fresh():raise ValueError("Stale output")
        sent=None
        if action.kind in {Kind.TEXT,Kind.TEXT_REACTION}:
            kwargs=dict(content=action.text,allowed_mentions=discord.AllowedMentions.none(),mention_author=False,nonce=event.response_to or event.id,suppress_embeds=True)
            sent=await current.reply(**kwargs)
        elif action.kind==Kind.STICKER:
            sticker=self.client.standard_stickers.get(int(action.asset))
            if not isinstance(sticker,discord.StandardSticker):raise ValueError('Only standard stickers')
            sent=await current.reply(stickers=[sticker],allowed_mentions=discord.AllowedMentions.none(),mention_author=False,nonce=event.response_to or event.id)
        if action.kind in {Kind.REACTION,Kind.TEXT_REACTION}:
            if not await fresh():raise ValueError("Stale reaction")
            await current.add_reaction(action.asset)
        return sent.id if sent else None


class OwnerPanel(discord.ui.View):
    def __init__(self,client):super().__init__(timeout=180);self.client=client
    async def interaction_check(self,interaction):
        return await self.client.owner_check(interaction)
    @discord.ui.button(label="중지",style=discord.ButtonStyle.danger)
    async def stop_bot(self,interaction,button):
        self.client.settings.set(interaction.user.id,"enabled",False)
        self.client.runtime.invalidate_all()
        await interaction.response.send_message("정지했어.",ephemeral=True)
    @discord.ui.button(label="활성화",style=discord.ButtonStyle.success)
    async def start(self,interaction,button):
        self.client.settings.set(interaction.user.id,"enabled",True)
        self.client.runtime.invalidate_all()
        await interaction.response.send_message("허용 범위에서 활성화했어. 장애 안전 중단은 프로세스를 재시작해 줘.",ephemeral=True)
    @discord.ui.select(placeholder="기분 선택",options=[discord.SelectOption(label=m,value=m) for m in sorted(MOODS)])
    async def mood(self,interaction,select):
        self.client.settings.set(interaction.user.id,"mood",select.values[0]);self.client.runtime.cancel_pending()
        await interaction.response.send_message("기분을 저장했어.",ephemeral=True)
    @discord.ui.button(label="상태",style=discord.ButtonStyle.secondary)
    async def status(self,interaction,button):
        await interaction.response.send_message(self.client.status_text(),ephemeral=True)


class EchoClient(discord.Client):
    def __init__(self,settings,backend,admin_guilds):
        intents=discord.Intents.none();intents.guilds=True;intents.guild_messages=True
        intents.message_content=True;intents.emojis_and_stickers=True;intents.guild_reactions=True
        super().__init__(intents=intents,allowed_mentions=discord.AllowedMentions.none(),max_messages=None,
                         member_cache_flags=discord.MemberCacheFlags.none())
        self.settings=settings;self.backend=backend;self.admin_guilds=admin_guilds
        self.tree=app_commands.CommandTree(self);self.cache=VisualCache(settings.path.parent/'visual.sqlite3');self.library=None
        self.standard_stickers={}
        self.user_names={}
        from .companion_store import CompanionStore
        self.companion=CompanionStore(settings.path.parent/'companion.sqlite3')
        self.runtime=Runtime(settings,backend,DiscordTransport(self),self.cache,self.library,
                             ledger_path=settings.path.parent/'sent.sqlite3',companion=self.companion)
        self.runtime.gateway_available=False
        self.owner_tasks=set()
        self.shutdown_lock=asyncio.Lock()
        self.install_commands()

    async def owner_check(self,interaction):
        try:self.settings.authorize(interaction.user.id)
        except PermissionError:
            if not interaction.response.is_done():await interaction.response.send_message("이 작업은 사용할 수 없어.",ephemeral=True)
            return False
        if interaction.guild_id not in self.admin_guilds:
            if not interaction.response.is_done():await interaction.response.send_message("로컬에서 등록한 관리 서버가 아니야.",ephemeral=True)
            return False
        return True

    def status_text(self):
        cfg=self.settings.get()
        return f"활성 {cfg['enabled']} / 안전 중단 {self.runtime.stopped} / 모델 {cfg['model']} / 기분 {cfg['mood']} / 활동 {cfg['activity']} / GPU 대기 {self.backend.pending} / 실험 시각 분석 {cfg['vision']}"

    def standard_catalog(self,content):
        hints=[]
        for text,tags in [('안녕','hello wave'),('축하','congratulations celebrate'),('고마','thank'),('잘 자','sleep goodnight'),('웃','laugh')]:
            if text in content:hints.extend(tags.split())
        ranked=[]
        for sticker in self.standard_stickers.values():
            if not isinstance(sticker,discord.StandardSticker):continue
            tags=' '.join(sticker.tags).lower()
            score=sum(h in tags for h in hints)
            if score:ranked.append((score,sticker))
        ranked.sort(key=lambda row:(-row[0],row[1].id))
        return {str(s.id):dict(official_description=(s.description or '')[:180],official_tags=s.tags[:12],source='Discord standard metadata; not pixel analysis') for _,s in ranked[:8]}

    def install_commands(self):
        client=self
        class OwnerGroup(app_commands.Group):
            async def interaction_check(self,interaction):return await client.owner_check(interaction)
        group=OwnerGroup(name="echo",description="EchoMate 관리")
        @group.command(name="panel",description="비공개 관리 패널")
        async def panel(i:discord.Interaction):
            await i.response.send_message(self.status_text(),view=OwnerPanel(self),ephemeral=True)
        @group.command(name="set",description="기분·성격·모델·기능 설정")
        @app_commands.choices(key=[app_commands.Choice(name=k,value=k) for k in ("enabled","text","reactions","stickers","vision","mood","gender","warmth","cuteness","playfulness","auto_mood","activity","cooldown","engagement_seconds","daily_limit","model")])
        async def setting(i:discord.Interaction,key:str,value:str):
            defaults=self.settings.get()
            if key not in defaults or key=="guilds":raise ValueError("Unknown setting")
            previous=defaults[key]
            if type(previous) is bool:
                if value not in ("true","false"):raise ValueError("true/false required")
                parsed=value=="true"
            elif type(previous) is int:parsed=int(value)
            elif type(previous) is float:parsed=float(value)
            else:parsed=value
            if key=='model':
                await i.response.defer(ephemeral=True)
                await self.runtime.switch_model(i.user.id,parsed)
                await i.followup.send('모델 준비와 선택 변경을 마쳤어.',ephemeral=True)
                return
            self.settings.set(i.user.id,key,parsed)
            if key=='enabled' and not parsed:self.runtime.invalidate_all()
            else:self.runtime.cancel_pending()
            await i.response.send_message("설정을 저장했어.",ephemeral=True)
        @setting.autocomplete('value')
        async def value_options(i:discord.Interaction,current:str):
            if i.user.id!=self.settings.owner_id:return []
            key=getattr(i.namespace,'key','')
            options=(sorted(MOODS) if key=='mood' else ['quiet','normal','active','very_active'] if key=='activity' else
                     ['base','persona','adult'] if key=='model' else ['female','male','neutral'] if key=='gender' else ['true','false'] if type(self.settings.get().get(key)) is bool else [])
            return [app_commands.Choice(name=v,value=v) for v in options if current in v]
        @group.command(name="scope",description="현재 서버의 채널·스레드 모드 설정")
        @app_commands.choices(mode=[app_commands.Choice(name=k,value=k) for k in ('silent','mention','autonomous','reaction')])
        async def set_scope(i:discord.Interaction,channel:discord.TextChannel|discord.ForumChannel|discord.Thread,mode:str,inherit:bool=False):
            if channel.guild.id!=i.guild_id:raise ValueError("Wrong guild")
            self.settings.set_scope(i.user.id,i.guild_id,channel.id,mode,thread=isinstance(channel,discord.Thread),inherit=inherit)
            self.runtime.invalidate_all()
            await i.response.send_message("범위를 저장했어. enabled가 켜져 있어야 동작해.",ephemeral=True)
        @group.command(name="guild",description="현재 관리 서버 활성화 또는 비활성화")
        async def guild(i:discord.Interaction,enabled:bool):
            def mutate(cfg):
                cfg["guilds"].setdefault(str(i.guild_id),dict(enabled=False,channels={},threads={}))['enabled']=enabled
            self.settings.change(i.user.id,mutate);self.runtime.invalidate_all()
            await i.response.send_message("서버 설정을 저장했어.",ephemeral=True)
        @group.command(name="cache",description="현재 서버 시각 캐시 삭제 또는 허용 채널에서 에셋 갱신")
        async def cache_command(i:discord.Interaction,refresh:bool=False,offset:int=0,limit:int=5):
            if not 0<=offset<=1000 or not 1<=limit<=10:raise ValueError("Invalid refresh page")
            self.runtime.blocked_assets={key for key in self.runtime.blocked_assets if key[0]!=i.guild_id}
            if not refresh:
                self.cache.clear(i.guild_id)
                await i.response.send_message("이 서버의 시각 캐시를 삭제했어.",ephemeral=True);return
            cfg=self.settings.get();parent=i.channel.parent_id if isinstance(i.channel,discord.Thread) else None
            if not cfg['vision'] or scope(cfg,i.guild_id,i.channel_id,parent)=="silent":raise ValueError("Vision requires an allowed active channel")
            await i.response.defer(ephemeral=True)
            processed=0
            task=asyncio.current_task();self.owner_tasks.add(task)
            try:
                for asset in [*i.guild.emojis,*i.guild.stickers][offset:offset+limit]:
                    self.settings.authorize(i.user.id)
                    if self.runtime.stopped or self.is_closed() or not self.settings.get()['vision'] or scope(self.settings.get(),i.guild_id,i.channel_id,parent)=="silent":break
                    prefix="emoji:" if isinstance(asset,discord.Emoji) else "sticker:"
                    try:await self.cache.analyze(i.guild_id,prefix+str(asset.id),await download(str(asset.url)),self.backend,force=True);processed+=1
                    except (ValueError,RuntimeError,OSError):self.runtime.note("owner_asset_refresh_failed")
            finally:self.owner_tasks.discard(task)
            if not self.is_closed():await i.followup.send(f"실제 이미지 분석 {processed}개 완료. 다음 offset은 {offset+limit}이야.",ephemeral=True)
        @group.command(name="shutdown",description="안전하게 종료")
        async def shutdown(i:discord.Interaction):
            await i.response.send_message("종료할게.",ephemeral=True)
            asyncio.create_task(self.close())
        for guild in self.admin_guilds:self.tree.add_command(group,guild=discord.Object(guild))
        @app_commands.choices(action=[app_commands.Choice(name=name,value=value) for name,value in [('기억 목록','목록'),('내 기억 전체 삭제','기억삭제'),('기억·관계·알림 모두 삭제','전체삭제'),('본인 자동 기억·관계 저장 허용','저장다시허용')]])
        async def own_memory(i:discord.Interaction,action:str):
            if not i.guild_id or str(i.guild_id) not in self.settings.get()['guilds']:
                await i.response.send_message('이 서버에는 관리할 기억이 없어.',ephemeral=True);return
            await i.response.defer(ephemeral=True)
            if action=='전체삭제':
                await asyncio.to_thread(self.companion.forget,i.guild_id,i.user.id)
                self.runtime.members.clear(i.guild_id,user=i.user.id)
                result='네 기억·관계·예약 기록을 삭제하고 자동 저장을 막았어.'
            elif action=='기억삭제':
                await asyncio.to_thread(self.companion.forget_memories,i.guild_id,i.user.id)
                result='이 서버의 네 기억을 지우고 기억 자동 저장을 막았어.'
            elif action=='저장다시허용':
                await asyncio.to_thread(self.companion.resume_subject,i.guild_id,i.user.id)
                result='이 서버에서 네 발언의 선택적 자동 기억과 숫자 관계 기록을 허용했어. 소유자 설정도 켜져 있어야 하며, 전체 삭제로 철회할 수 있어. 가중치 학습에는 쓰지 않아.'
            else:
                rows=await asyncio.to_thread(self.companion.memories,i.guild_id,i.user.id,i.channel_id)
                result='현재 이 채널에서 사용할 수 있는 기억이 없어.' if not rows else '\n'.join(r['summary'] for r in rows[:5])
            await i.followup.send(result,ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
        command=app_commands.Command(name='내기억',description='자신의 로컬 기억 조회·삭제·저장 동의 관리',callback=own_memory)
        for guild in self.admin_guilds:self.tree.add_command(command,guild=discord.Object(guild))

        @self.tree.error
        async def command_error(i,error):
            self.runtime.note("owner_command_failed")
            if not i.response.is_done():await i.response.send_message("처리하지 못했어. 입력값과 로컬 진단을 확인해 줘.",ephemeral=True)
            else:await i.followup.send("처리하지 못했어. 설정과 파일 지원 범위를 확인해 줘.",ephemeral=True)

    async def setup_hook(self):
        try:
            self.standard_stickers={s.id:s for pack in await self.fetch_premium_sticker_packs() for s in pack.stickers if isinstance(s,discord.StandardSticker)}
        except discord.HTTPException:self.runtime.note('standard_sticker_catalog_unavailable')
        for guild in self.admin_guilds:await self.tree.sync(guild=discord.Object(guild))

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
        standard=tuple(dict(id=str(s.id),official_description=(s.description or '')[:180],official_tags=s.tags[:12]) for item in message.stickers if (s:=self.standard_stickers.get(item.id)))
        await self.runtime.ingest(Event(message.id,message.guild.id,message.channel.id,message.author.id,
            message.content,message.created_at,parent=parent,reply_to=message.reference.message_id if message.reference else None,
            assets=assets_from_message(message) if cfg['vision'] else (),standard_stickers=standard,received_at=received,
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
        self.cache.retain(guild.id,set(),"sticker:");self.runtime.invalidate_guild(guild.id)

    async def close(self):
        async with self.shutdown_lock:
            if self.is_closed():return
            tasks=[task for task in self.owner_tasks if task is not asyncio.current_task()]
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            await self.runtime.close()
            await super().close()
