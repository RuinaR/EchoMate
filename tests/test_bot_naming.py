"""Synthetic guild identities, name addressing and running-list regressions."""
import asyncio
import queue
import secrets
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import test_bot_integration as integration
from echomate_bot.desktop import LocalController
from echomate_bot.desktop_ui import DesktopApp
from echomate_bot.naming import validate_name,name_candidate,guild_name
from echomate_bot.settings import Settings
from echomate_studio.implicit_address import ImplicitAddress


class NameForms(unittest.TestCase):
    def test_vocatives_are_bounded_not_arbitrary_substrings(self):
        for value in ('별빛봇','별빛봇아 안녕','별빛아 질문 있어','별빛야, 안녕','별빛 안녕'):
            self.assertTrue(name_candidate(value,'별빛봇'),value)
        for value in ('별빛봇은 어제 왔어','다른별빛아','"별빛아"라고 부르면 돼','`별빛아`','https://example.invalid/별빛아'):
            self.assertFalse(name_candidate(value,'별빛봇'),value)
        for value in ('','a','x'*33,'별빛\n봇','<@999>','별빛\u200b봇'):
            with self.assertRaises(ValueError):validate_name(value)


class NamedRuntime(unittest.IsolatedAsyncioTestCase):
    setUp=integration.BotIntegration.setUp
    asyncTearDown=integration.BotIntegration.asyncTearDown
    event=integration.BotIntegration.event
    settle=integration.BotIntegration.settle

    def rename(self):
        self.settings.change(1,lambda cfg:cfg['guilds']['2'].update(name='별빛봇'))

    async def test_first_named_call_works_in_mention_only_scope_without_probability(self):
        self.rename();self.settings.set(1,'activity','quiet')
        await self.runtime.ingest(self.event(content='별빛아 안녕'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)
        metadata=self.backend.calls[0][-1]['content']
        self.assertIn('configured_bot_name',metadata)
        self.assertEqual(self.transport.sent[0][0].id,10)

    async def test_name_candidate_never_skips_semantic_addressee_check(self):
        self.rename();self.backend.continuity=AsyncMock(return_value=ImplicitAddress(False,False))
        await self.runtime.ingest(self.event(content='별빛아, 저 사람한테 말하는 거야'));await self.settle()
        self.backend.continuity.assert_awaited_once()
        self.assertFalse(self.transport.sent)

    async def test_wrong_guild_and_unallowed_channels_do_not_gain_access_from_name(self):
        self.rename()
        await self.runtime.ingest(self.event(channel=5,content='별빛아 안녕'));await self.settle()
        self.assertFalse(self.backend.calls)
        self.assertEqual(guild_name(self.settings.get(),55),'EchoMate')


class NameControls(unittest.IsolatedAsyncioTestCase):
    async def test_owner_local_name_persists_without_enabling_guild_or_accepting_unknown_guild(self):
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            c=LocalController.__new__(LocalController)
            c.settings=Settings(1,secrets.token_hex(32),Path(directory)/'settings.json')
            c.bootstrap=dict(owner_id=1,admin_guilds=[2]);c.client=None;c.job=None
            c.phase='';c.error='';c.updates=queue.Queue(8)
            await c.command('name',guild=2,name='별빛봇')
            self.assertEqual(guild_name(c.settings.get(),2),'별빛봇')
            self.assertFalse(c.settings.get()['guilds']['2']['enabled'])
            restored=Settings(1,c.settings._key.decode(),c.settings.path)
            self.assertEqual(guild_name(restored.get(),2),'별빛봇')
            revision=c.settings.revision
            await c.command('name',guild=99,name='다른봇')
            self.assertEqual(c.error,'PermissionError');self.assertEqual(c.settings.revision,revision)

    async def test_nickname_sdk_call_targets_only_own_member_and_configured_guild(self):
        from echomate_bot.discord_app import EchoClient
        member=SimpleNamespace(nick='old',edit=AsyncMock())
        client=SimpleNamespace(get_guild=lambda gid:SimpleNamespace(me=member) if gid==2 else None,
            settings=SimpleNamespace(get=lambda:dict(guilds={'2':dict(name='별빛봇')})))
        await EchoClient.apply_guild_name(client,2)
        member.edit.assert_awaited_once_with(nick='별빛봇',reason='Owner configured bot name')
        await EchoClient.apply_guild_name(client,3)
        self.assertEqual(member.edit.await_count,1)


class ActiveChannelList(unittest.TestCase):
    def test_running_filters_rules_and_inherited_threads_with_full_list_escape(self):
        with tempfile.TemporaryDirectory(dir='local_data') as directory:
            cfg=Settings(1,secrets.token_hex(32),Path(directory)/'settings.json')
            cfg.set_activity_scope(1,2,3,'mention','silent',inherit=True)
            cfg.set_activity_scope(1,2,5,'silent','silent',thread=True)
            root=tk.Tk();root.withdraw()
            try:
                app=DesktopApp(root,SimpleNamespace(submit=lambda *a,**k:None))
                app.snapshot=dict(cfg=cfg.get(),running=True,servers=[dict(id=2,label='synthetic',enabled=True,channels=[
                    dict(id=3,label='active',thread=False),dict(id=4,label='inherited',thread=True,parent=3),
                    dict(id=5,label='blocked',thread=True,parent=3),dict(id=6,label='unconfigured',thread=False)])],
                    connected=False,phase='',error='',notice='',pending=0,contexts=0,latency=None,progress=[])
                app.refresh_lists()
                self.assertEqual({i['id'] for i in app.channel_list.items},{3,4})
                app.toggle_channel_view()
                self.assertEqual(len(app.channel_list.items),4)
                app.show_all=False;app.snapshot['running']=False;app.refresh_lists()
                self.assertEqual(len(app.channel_list.items),4)
            finally:
                app.destroy();app=None;root=None
                import gc
                gc.collect()
