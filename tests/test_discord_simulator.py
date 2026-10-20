"""Real discord.py objects and serialization; HTTP boundary stays in memory.

No login, token, gateway, slash sync or socket is used. This checks application
and SDK integration, not Discord's remote rate-limit implementation.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import secrets
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,AsyncMock

import discord
from echomate_bot.actions import Action, Kind
from echomate_bot.discord_app import EchoClient
from echomate_bot.runtime import Event
from echomate_bot.settings import Settings
from test_bot_integration import FakeBackend


def user(uid=4):
    return dict(id=str(uid), username='synthetic', discriminator='0001', avatar=None, bot=uid == 999)


def payload(mid, channel=3, content='<@999> 안녕', author=4):
    return dict(id=str(mid), channel_id=str(channel), guild_id='2', type=0,
                content=content, author=user(author), attachments=[], embeds=[],
                mentions=[user(999)], mention_roles=[], pinned=False,
                mention_everyone=False, timestamp='2026-10-19T00:00:00+00:00',
                edited_timestamp=None, tts=False, flags=0)


class MemoryHTTP:
    """Deliberately no forwarding fallback: unexpected endpoint fails the test."""
    def __init__(self):
        self.messages = {}
        self.sends = []
        self.reactions = []
        self.failure = None

    async def get_member(self, guild, uid):
        return dict(user=user(uid), roles=[], joined_at='2026-10-19T00:00:00+00:00', flags=0)

    async def get_message(self, channel, mid):
        if (channel, mid) not in self.messages:
            raise discord.NotFound(SimpleNamespace(status=404, reason='Not Found'), dict(code=10008, message='Synthetic missing message'))
        return deepcopy(self.messages[channel, mid])

    async def send_message(self, channel, *, params):
        if self.failure:
            raise self.failure
        data = deepcopy(params.payload)
        self.sends.append((channel, data))
        result = payload(9000 + len(self.sends), channel, data.get('content', ''), 999)
        result.update({k: data[k] for k in ('message_reference', 'nonce') if k in data})
        self.messages[channel, int(result['id'])] = result
        return result

    async def add_reaction(self, channel, mid, emoji):
        self.reactions.append((channel, mid, emoji))

    async def send_typing(self, channel):
        pass


class DiscordSDKSimulation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='local_data')
        self.settings = Settings(1, secrets.token_hex(32), Path(self.temp.name) / 'settings.json')
        self.settings.set_scope(1, 2, 3, 'mention')
        self.settings.set(1, 'enabled', True)
        self.network_guard = patch('discord.http.HTTPClient.request', side_effect=AssertionError('Network forbidden in simulator'))
        self.network_guard.start()
        self.client = EchoClient(self.settings, FakeBackend(), [2])
        await self.client._async_setup_hook()
        state = self.client._connection
        state.user = discord.ClientUser(state=state, data=user(999))
        self.http = MemoryHTTP()
        state.http = self.http
        guild = discord.Guild(state=state, data=dict(id='2', name='Synthetic guild', owner_id='1',
            roles=[dict(id='2', name='@everyone', permissions=str(discord.Permissions.all().value), position=0, color=0)],
            members=[dict(user=user(999), roles=[], flags=0)],
            channels=[dict(id='3', name='allowed', type=0, position=0, permission_overwrites=[]),
                      dict(id='8', name='blocked', type=0, position=1, permission_overwrites=[])],
            threads=[dict(id='30', parent_id='3', owner_id='4', name='Synthetic thread', type=11,
                          message_count=0, member_count=1, thread_metadata=dict(archived=False,
                          archive_timestamp='2026-10-19T00:00:00+00:00', auto_archive_duration=60, locked=False))]))
        state._add_guild(guild)
        self.guild = guild
        self.client._ready.set()
        self.client.runtime.gateway_available = True

    async def asyncTearDown(self):
        try:
            await self.client.close()
        finally:
            self.network_guard.stop()
            self.temp.cleanup()

    def message(self, mid=100, channel=3, content='<@999> 안녕', author=4):
        data = payload(mid, channel, content, author)
        self.http.messages[channel, mid] = data
        return self.client._connection.create_message(channel=self.guild.get_channel_or_thread(channel), data=data)

    def event(self, mid=100, channel=3):
        return Event(mid, 2, channel, 4, '<@999> 안녕', datetime.now(timezone.utc), parent=3 if channel == 30 else None)

    async def test_gateway_handler_to_runtime_to_real_sdk_reply_serialization(self):
        await self.client.on_message(self.message())
        await asyncio.wait_for(asyncio.gather(*list(self.client.runtime.tasks.values())), 5)
        self.assertEqual(len(self.http.sends), 1)
        channel, body = self.http.sends[0]
        self.assertEqual(channel, 3)
        self.assertEqual(int(body['message_reference']['message_id']), 100)
        self.assertEqual(int(body['nonce']), 100)
        self.assertEqual(body['allowed_mentions']['parse'], [])
        self.assertFalse(body['allowed_mentions']['replied_user'])
        self.assertTrue(body['flags'] & 4)

    async def test_social_engine_followup_and_reaction_reach_sdk_with_exact_sources(self):
        from echomate_bot.social import SocialDecision
        runtime=self.client.runtime;runtime.direct_cooldown=0
        self.client.backend.fast_text_path=True
        self.client.backend.assess_social=AsyncMock(return_value=SocialDecision('bot','continue','0','question',True))
        first=discord.utils.time_snowflake(datetime.now(timezone.utc))
        await self.client.on_message(self.message(mid=first,content='<@999>같이 얘기해 보자'))
        await asyncio.gather(*list(runtime.tasks.values()));await asyncio.sleep(.02)
        second=discord.utils.time_snowflake(datetime.now(timezone.utc))
        data=payload(second,content='그건 왜 그런 건데');data['mentions']=[]
        self.http.messages[3,second]=data
        message=self.client._connection.create_message(channel=self.guild.get_channel(3),data=data)
        await self.client.on_message(message)
        while runtime.tasks or runtime.utterances.pending or runtime.utterances.emitting:
            await asyncio.gather(*list(runtime.tasks.values()),*(r.task for r in runtime.utterances.pending.values()),*runtime.utterances.emitting,return_exceptions=True)
        self.assertEqual([int(body['message_reference']['message_id']) for channel,body in self.http.sends],[first,second])
        self.client.backend.assess_social.assert_awaited_once()
        self.settings.set(1,'reactions',True);await asyncio.sleep(.02)
        third=discord.utils.time_snowflake(datetime.now(timezone.utc))
        await self.client.on_message(self.message(mid=third,content='<@999> 이 메시지에 👍 달아줘'))
        await asyncio.gather(*list(runtime.tasks.values()))
        self.assertEqual(self.http.reactions,[(3,third,'👍')]);self.assertEqual(len(self.http.sends),2)
        for channel,body in self.http.sends:self.assertEqual(body['allowed_mentions']['parse'],[])

    async def test_direct_unicode_request_calls_real_sdk_reaction_not_text(self):
        self.settings.set(1,'reactions',True)
        mid=discord.utils.time_snowflake(datetime.now(timezone.utc))
        await self.client.on_message(self.message(mid=mid,content='<@999> 이 메시지에 👍 달아줘'))
        await asyncio.wait_for(asyncio.gather(*list(self.client.runtime.tasks.values())),5)
        self.assertEqual(self.http.reactions,[(3,mid,'👍')]);self.assertFalse(self.http.sends);self.assertFalse(self.client.backend.calls)

    async def test_permission_cache_reuses_reads_and_forces_final_send_check(self):
        self.message();transport=self.client.runtime.transport
        with patch.object(self.http,'get_member',wraps=self.http.get_member) as read:
            for _ in range(5):await transport.permissions(self.event())
            self.assertEqual(read.await_count,1)
            await transport.execute(self.event(),Action(Kind.TEXT,'합성 응답'),None,AsyncMock(return_value=True))
            self.assertEqual(read.await_count,2)

    async def test_eleven_source_reads_are_unique_even_with_middle_reaction_target(self):
        from dataclasses import replace
        from echomate_bot.utterances import Utterances
        parts=[]
        for mid in range(100,111):
            self.message(mid=mid)
            parts.append(replace(self.event(mid),content='<@999> 안녕'))
        event=replace(Utterances.compose(parts,'utt:sdk-eleven'),reaction_target=105)
        with patch.object(self.http,'get_message',wraps=self.http.get_message) as read:
            await self.client.runtime.transport.execute(event,Action(Kind.TEXT_REACTION,'합성 답변',asset='👍',target=105),None,AsyncMock(return_value=True))
        self.assertEqual(read.await_count,11)
        self.assertEqual({call.args for call in read.await_args_list},{(3,mid) for mid in range(100,111)})
        self.assertEqual(int(self.http.sends[0][1]['message_reference']['message_id']),100)
        self.assertEqual(self.http.reactions,[(3,105,'👍')])

    async def test_reaction_reply_target_and_permission_revocation(self):
        self.message();self.message(mid=99)
        from dataclasses import replace
        event=replace(self.event(),reply_to=99)
        await self.client.runtime.transport.execute(event,Action(Kind.REACTION,asset='👍',target=99),None,AsyncMock(return_value=True))
        self.assertEqual(self.http.reactions,[(3,99,'👍')]);self.assertFalse(self.http.sends)
        with patch.object(self.client.runtime.transport,'_permissions',AsyncMock(return_value=dict(view=True,send=True,react=False))):
            with self.assertRaises(PermissionError):await self.client.runtime.transport.execute(event,Action(Kind.REACTION,asset='👍'),None,AsyncMock(return_value=True))
        self.assertEqual(len(self.http.reactions),1)

    async def test_autonomous_reaction_uses_sdk_and_keeps_other_addressee_silent(self):
        from echomate_bot.dialogue_intent import DialogueIntent
        import random
        class Opportunity(random.Random):
            def random(self):return 0
        self.settings.set_activity_scope(1,2,3,'silent','autonomous');self.settings.set(1,'reactions',True)
        runtime=self.client.runtime;runtime.rng=Opportunity();runtime.autonomy_idle_since-=1000
        self.client.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('information','group','new',True));self.client.backend.action='REACTION'
        await self.client.on_message(self.message(content='여러분 준비하던 행사를 무사히 마쳤어'))
        await asyncio.gather(*list(runtime.tasks.values()))
        self.assertEqual(self.http.reactions,[(3,100,'👍')]);self.assertFalse(self.http.sends);self.assertFalse(self.client.backend.calls)
        await self.client.on_message(self.message(mid=101,content='<@5> 아까 말한 건 너한테만 얘기할게'))
        await asyncio.gather(*list(runtime.tasks.values()))
        self.assertEqual(len(self.http.reactions),1)

    async def test_word_reaction_on_confirmed_previous_own_message_keeps_reply_source(self):
        self.settings.set(1,'reactions',True);self.client.runtime.direct_cooldown=0
        self.settings.set(1,'web_search',True)
        # This ordinary visible message must have reached the local context first.
        first=discord.utils.time_snowflake(datetime.now(timezone.utc));await self.client.on_message(self.message(mid=first,content='<@999> 지금 한 판 이겼어'))
        await asyncio.gather(*list(self.client.runtime.tasks.values()))
        await asyncio.sleep(.01)
        second=discord.utils.time_snowflake(datetime.now(timezone.utc));await self.client.on_message(self.message(mid=second,content='<@999> 내가 방금 쓴 글에 하트 달아줘'))
        await asyncio.gather(*list(self.client.runtime.tasks.values()))
        self.assertEqual(self.http.reactions,[(3,first,'❤️')]);self.assertEqual(len(self.http.sends),1)

    async def test_gateway_resources_close_even_if_model_shutdown_fails(self):
        original=self.client.runtime.close
        await original()
        self.client.runtime.close=AsyncMock(side_effect=RuntimeError('Synthetic shutdown failure'))
        with self.assertRaises(RuntimeError):await self.client.close()
        self.assertTrue(self.client.is_closed())

    async def test_member_payload_and_actual_reply_metadata_without_members_intent(self):
        captured=AsyncMock();self.client.runtime.ingest=captured
        mid=discord.utils.time_snowflake(datetime.now(timezone.utc))
        original=payload(mid-1,content='앞선 실제 메시지',author=5)
        data=payload(mid,content='가온아 <@5> 이거 봐',author=4)
        data['mentions']=[dict(user(5),username='gaon',member=dict(nick='가온mk2',roles=[],flags=0))]
        data['message_reference']=dict(message_id=str(mid-1),channel_id='3',guild_id='2')
        data['referenced_message']=original
        message=self.client._connection.create_message(channel=self.guild.get_channel(3),data=data)
        await self.client.on_message(message)
        e=captured.call_args.args[0]
        self.assertEqual(e.reply_author,5);self.assertEqual(e.reply_to,mid-1);self.assertEqual(e.member_mentions,(5,))
        self.assertIn('가온mk2',dict(e.member_names)[5]);self.assertFalse(self.client.intents.members)
        self.assertFalse(self.http.sends)

    async def test_member_cache_cleared_on_scope_permission_change_and_guild_departure(self):
        self.client.runtime.members.observe(2,3,4,('가온',))
        await self.client.on_guild_channel_update(self.guild.get_channel(3),self.guild.get_channel(3))
        self.assertFalse(self.client.runtime.members.people)
        self.client.companion.set_alias(2,3,4,'구름')
        await self.client.on_guild_remove(self.guild)
        self.assertFalse(self.client.companion.aliases(2))

    async def test_approved_alias_lookup_fetches_only_requested_member_and_handles_departure(self):
        transport=self.client.runtime.transport
        with patch.object(self.http,'get_member',wraps=self.http.get_member) as fetch:
            rows=await transport.member_lookup(self.event(),[5])
        self.assertEqual(rows[0][0],5);fetch.assert_awaited_once_with(2,5)
        self.client.companion.set_alias(2,3,5,'별빛')
        missing=discord.NotFound(SimpleNamespace(status=404,reason='Not Found'),dict(code=10007,message='Unknown Member'))
        with patch.object(self.http,'get_member',side_effect=missing):self.assertFalse(await transport.member_lookup(self.event(),[5]))
        self.assertFalse(self.client.companion.aliases(2,3))

    async def test_blocked_channel_and_bot_events_never_reach_inference_or_http(self):
        await self.client.on_message(self.message(channel=8))
        await self.client.on_message(self.message(mid=101, author=999))
        self.assertEqual(self.client.backend.calls, [])
        self.assertEqual(self.http.sends, [])

    async def test_name_then_unpunctuated_followup_through_sdk_keep_distinct_replies(self):
        from echomate_bot.dialogue_intent import DialogueIntent
        self.settings.change(1,lambda c:c['guilds']['2'].update(name='다온봇'))
        self.client.runtime.direct_cooldown=0
        self.client.backend.assess_dialogue=AsyncMock(return_value=DialogueIntent('question','bot','continue',True))
        sources=[]
        for text in ('다온아','어떤 생각하고있었어'):
            await asyncio.sleep(.01)
            mid=discord.utils.time_snowflake(datetime.now(timezone.utc));sources.append(mid)
            await self.client.on_message(self.message(mid=mid,content=text))
            # A completed bare call may wait for a bounded supplement; settle
            # that logical utterance before testing a distinct later follow-up.
            runtime=self.client.runtime
            while runtime.utterances.pending or runtime.utterances.emitting or runtime.tasks:
                waits=[r.task for r in runtime.utterances.pending.values()]+list(runtime.utterances.emitting)+list(runtime.tasks.values())
                await asyncio.wait_for(asyncio.gather(*waits),5)
        self.assertEqual([int(b['message_reference']['message_id']) for _,b in self.http.sends],sources)
        self.client.backend.assess_dialogue.assert_awaited_once()

    async def test_thread_permissions_reaction_and_standard_sticker_keep_source(self):
        self.message(channel=30)
        transport = self.client.runtime.transport
        event = self.event(channel=30)
        self.assertTrue((await transport.permissions(event))['send'])
        async def fresh(): return True
        await transport.execute(event, Action(Kind.REACTION, asset='👍'), None, fresh)
        self.assertEqual(self.http.reactions, [(30, 100, '👍')])
        with self.assertRaises(ValueError):await transport.execute(event,Action(Kind.STICKER,asset='77'),None,fresh)
        self.assertFalse(self.http.sends)
        self.guild.get_thread(30).archived = True
        self.assertEqual(await transport.permissions(event), {})

    async def test_deleted_source_and_http_forbidden_do_not_report_success(self):
        transport = self.client.runtime.transport
        async def fresh(): return True
        with self.assertRaises(discord.NotFound):
            await transport.execute(self.event(), Action(Kind.TEXT, '합성 답변'), None, fresh)
        self.message()
        self.http.failure = discord.Forbidden(SimpleNamespace(status=403, reason='Forbidden'), dict(code=50013, message='Synthetic permission denied'))
        with self.assertRaises(discord.Forbidden):
            await transport.execute(self.event(), Action(Kind.TEXT, '합성 답변'), None, fresh)
        self.assertEqual(self.http.sends, [])
