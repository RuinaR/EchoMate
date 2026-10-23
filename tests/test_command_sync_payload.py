"""Actual SDK command serialization/HTTP dispatch, in-memory remote scopes only."""
import json
from unittest.mock import AsyncMock,patch
import unittest
import test_bot_integration as base
from echomate_bot.discord_app import EchoClient


class CommandPayload(unittest.IsolatedAsyncioTestCase):
    setUp=base.BotIntegration.setUp
    asyncTearDown=base.BotIntegration.asyncTearDown

    async def test_real_sdk_global_consent_survives_empty_guild_sync(self):
        client=EchoClient(self.settings,self.backend,[2]);client._connection.application_id=42
        remote={None:[dict(id='100',application_id='42',name='old',description='legacy',type=1,version='1')],2:[]}
        captured=[]
        async def global_get(app):self.assertEqual(app,42);return remote[None]
        async def guild_get(app,guild):self.assertEqual(app,42);return remote[guild]
        async def write(app,*,payload,guild=None):
            self.assertEqual(app,42);captured.append((guild,json.loads(json.dumps(payload))))
            remote[guild]=[dict(p,id=str(200+i),application_id=str(app),version='2') for i,p in enumerate(payload)]
            return remote[guild]
        async def guild_write(app,guild,*,payload):return await write(app,guild=guild,payload=payload)
        try:
            with patch('discord.http.HTTPClient.request',new=AsyncMock(side_effect=AssertionError('Real Discord forbidden'))) as outbound,patch('aiohttp.ClientSession._request',new=AsyncMock(side_effect=AssertionError('Network forbidden'))),patch.object(client.tree._http,'get_global_commands',side_effect=global_get),patch.object(client.tree._http,'get_guild_commands',side_effect=guild_get),patch.object(client.tree._http,'bulk_upsert_global_commands',side_effect=write),patch.object(client.tree._http,'bulk_upsert_guild_commands',side_effect=guild_write):
                plan=await client.review_commands(1);await client.apply_commands(1,plan['fingerprint'])
                self.assertEqual(captured[0][0],None)
                self.assertEqual([(p['name'],p['type']) for p in captured[0][1]],[('동의',1),('성격',1)])
                self.assertFalse(captured[0][1][0].get('dm_permission',True))
                self.assertEqual(captured[1],(2,[]))
                self.assertEqual([p['name'] for p in remote[None]],['동의','성격']);self.assertEqual(remote[2],[])
                self.assertFalse(self.settings.get()['command_sync_pending']);outbound.assert_not_awaited()
        finally:await client.close()

    async def test_empty_local_tree_rejected_before_any_sdk_write(self):
        client=EchoClient(self.settings,self.backend,[2]);client._connection.application_id=42
        try:
            with patch.object(client.tree._http,'get_global_commands',new=AsyncMock(return_value=[])),patch.object(client.tree._http,'get_guild_commands',new=AsyncMock(return_value=[])),patch.object(client.tree._http,'bulk_upsert_global_commands',new=AsyncMock()) as write,patch('discord.http.HTTPClient.request',new=AsyncMock(side_effect=AssertionError('Real Discord forbidden'))):
                plan=await client.review_commands(1);client.tree.clear_commands(guild=None)
                with self.assertRaisesRegex(ValueError,'Unexpected local command contract'):await client.apply_commands(1,plan['fingerprint'])
                write.assert_not_awaited()
        finally:await client.close()
