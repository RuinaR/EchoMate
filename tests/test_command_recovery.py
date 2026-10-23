"""Actual CommandTree serialization, isolated HTTP and explicit failure stages."""
import asyncio
from contextlib import ExitStack
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch
import discord
import test_bot_integration as fixtures
from echomate_bot.discord_app import EchoClient


class CommandRecovery(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.BotIntegration.setUp
    asyncTearDown=fixtures.BotIntegration.asyncTearDown

    def client(self):
        c=EchoClient(self.settings,self.backend,[2]);c._connection.application_id=42
        return c

    def http(self,client,*,bad_global=None):
        state=dict(global_rows=[dict(id='100',application_id='42',name='legacy',description='old',type=1,version='1')],
            guild_rows=[dict(id='101',application_id='42',guild_id='2',name='legacy',description='old',type=1,version='1')])
        async def global_write(app,*,payload):
            state['global_rows']=bad_global if bad_global is not None else [dict(p,id='200',application_id=str(app),version='2') for p in payload]
            return state['global_rows']
        async def guild_write(app,guild,*,payload):state['guild_rows']=[];return []
        stack=ExitStack()
        stack.enter_context(patch('discord.http.HTTPClient.request',new=AsyncMock(side_effect=AssertionError('Real Discord forbidden'))))
        stack.enter_context(patch('aiohttp.ClientSession._request',new=AsyncMock(side_effect=AssertionError('External network forbidden'))))
        get_global=stack.enter_context(patch.object(client.tree._http,'get_global_commands',new=AsyncMock(side_effect=lambda app:state['global_rows'])))
        get_guild=stack.enter_context(patch.object(client.tree._http,'get_guild_commands',new=AsyncMock(side_effect=lambda app,guild:state['guild_rows'])))
        put_global=stack.enter_context(patch.object(client.tree._http,'bulk_upsert_global_commands',new=AsyncMock(side_effect=global_write)))
        put_guild=stack.enter_context(patch.object(client.tree._http,'bulk_upsert_guild_commands',new=AsyncMock(side_effect=guild_write)))
        return stack,state,get_global,get_guild,put_global,put_guild

    async def test_global_verification_precedes_any_guild_cleanup(self):
        c=self.client();stack,state,_,_,put,guild_put=self.http(c,bad_global=[])
        try:
            with stack:
                plan=await c.review_commands(1)
                with self.assertRaisesRegex(ValueError,'verification'):await c.apply_commands(1,plan['fingerprint'])
                put.assert_awaited_once();guild_put.assert_not_awaited()
                self.assertEqual(state['guild_rows'][0]['name'],'legacy')
                audit=json.loads((self.root/'command-audit.json').read_text(encoding='utf-8'))
                self.assertEqual(audit['stage'],'verify_global');self.assertEqual(audit['status'],'failed')
                self.assertTrue(self.settings.get()['command_sync_pending']);self.assertIsNone(c.command_review)
        finally:await c.close()

    async def test_access_fields_change_requires_new_review_even_with_same_id_name(self):
        c=self.client();stack,state,_,_,put,guild_put=self.http(c)
        try:
            with stack:
                plan=await c.review_commands(1)
                state['global_rows'][0]['default_member_permissions']='0'
                with self.assertRaisesRegex(ValueError,'list changed'):await c.apply_commands(1,plan['fingerprint'])
                put.assert_not_awaited();guild_put.assert_not_awaited();self.assertIsNone(c.command_review)
        finally:await c.close()

    async def test_wrong_context_or_admin_gate_is_not_verified_by_name_alone(self):
        for change in (dict(contexts=[1]),dict(default_member_permissions='0'),dict(type=2),dict(integration_types=[1]),dict(nsfw=True)):
            c=self.client()
            bad=[dict(id='200',application_id='42',name='동의',description='test',type=1,contexts=[0],integration_types=[0],**{})]
            bad[0].update(change);stack,_,_,_,_,guild_put=self.http(c,bad_global=bad)
            try:
                with stack:
                    plan=await c.review_commands(1)
                    with self.assertRaisesRegex(ValueError,'verification'):await c.apply_commands(1,plan['fingerprint'])
                    guild_put.assert_not_awaited()
            finally:await c.close()

    async def test_read_forbidden_discards_stale_plan_and_records_safe_stage(self):
        c=self.client();stack,_,_,get_guild,put,_=self.http(c)
        try:
            with stack:
                await c.review_commands(1)
                get_guild.side_effect=discord.Forbidden(SimpleNamespace(status=403,reason='Forbidden'),dict(code=50001,message='sensitive text must not be logged'))
                with self.assertRaises(discord.Forbidden):await c.review_commands(1)
                self.assertIsNone(c.command_review);put.assert_not_awaited()
                self.assertEqual(c.command_status['stage'],'read_guild');self.assertEqual(c.command_status['http_status'],403)
                self.assertNotIn('sensitive',str(c.command_status))
        finally:await c.close()

    async def test_cancelled_write_keeps_pending_without_reusing_approval(self):
        c=self.client();stack,_,_,_,put,guild_put=self.http(c)
        try:
            with stack:
                plan=await c.review_commands(1);put.side_effect=asyncio.CancelledError()
                with self.assertRaises(asyncio.CancelledError):await c.apply_commands(1,plan['fingerprint'])
                guild_put.assert_not_awaited();self.assertIsNone(c.command_review)
                audit=json.loads((self.root/'command-audit.json').read_text(encoding='utf-8'))
                self.assertEqual(audit['status'],'cancelled');self.assertEqual(audit['stage'],'write_global')
                self.assertTrue(self.settings.get()['command_sync_pending'])
        finally:await c.close()

    async def test_explicit_public_scope_and_api_only_success(self):
        c=self.client();stack,_,_,_,put,_=self.http(c)
        try:
            with stack:
                plan=await c.review_commands(1);await c.apply_commands(1,plan['fingerprint'])
                payload=put.call_args.kwargs['payload'][0]
                self.assertEqual(payload['contexts'],[0]);self.assertEqual(payload['integration_types'],[0])
                self.assertIsNone(payload['default_member_permissions'])
                audit=json.loads((self.root/'command-audit.json').read_text(encoding='utf-8'))
                self.assertEqual(audit['stage'],'api_verified');self.assertEqual(audit['client_visibility'],'not_verified')
                self.settings.set(1,'command_sync_pending',True);put.reset_mock()
                await c.setup_hook();put.assert_not_awaited()
        finally:await c.close()

    async def test_wrong_guild_or_application_cannot_be_approved(self):
        for field,value in (('guild_id','3'),('application_id','43')):
            c=self.client();stack,state,_,_,put,_=self.http(c);state['guild_rows'][0][field]=value
            try:
                with stack:
                    with self.assertRaises(ValueError):await c.review_commands(1)
                    self.assertIsNone(c.command_review);put.assert_not_awaited()
            finally:await c.close()
