"""Local app-command serialization/callbacks; no remote Discord request."""
from pathlib import Path
import secrets
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch

from echomate_bot.character_models import character
from echomate_bot.character_store import CharacterStores
from echomate_bot.command_contract import command_access,consent_contract
from echomate_bot.discord_app import EchoClient
from echomate_bot.settings import Settings


class CharacterCommand(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder=tempfile.TemporaryDirectory(dir='local_data');root=Path(self.folder.name)
        settings=Settings(1,secrets.token_hex(32),root/'settings.json')
        store=CharacterStores.create(root/'personal.sqlite3').for_character('lime')
        self.backend=SimpleNamespace(character_id='lime',entry=character('lime'),name='유나',model=True,failed=False,close=AsyncMock())
        self.client=EchoClient(settings,self.backend,[2],companion=store)

    async def asyncTearDown(self):
        await self.client.close();self.folder.cleanup()

    async def test_new_mode_has_only_consent_and_character_wire_contract(self):
        commands=self.client.tree.get_commands()
        payload=[c.to_dict(self.client.tree) for c in commands]
        self.assertEqual([c.name for c in commands],['동의','캐릭터'])
        self.assertTrue(consent_contract(payload,mode='pretrained'))
        self.assertFalse(consent_contract(payload))
        self.assertEqual(command_access(),{'동의':'self_ephemeral','성격':'owner_ephemeral'})
        with self.assertRaises(ValueError):command_access('unknown')

    async def test_readonly_public_ephemeral_current_state_without_inference_or_db(self):
        interaction=SimpleNamespace(guild_id=2,user=SimpleNamespace(id=5),response=SimpleNamespace(send_message=AsyncMock()))
        with (patch.object(self.client.companion,'db',side_effect=AssertionError('No private store reads')),
              patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord'))):
            await self.client.tree.get_command('캐릭터').callback(interaction)
        kwargs=interaction.response.send_message.await_args.kwargs
        self.assertTrue(kwargs['ephemeral'])
        embed=kwargs['embed'].to_dict()
        self.assertIn('유나',str(embed));self.assertNotIn('local_data',str(embed))

    async def test_failed_transition_cannot_display_model_ready(self):
        interaction=SimpleNamespace(guild_id=2,response=SimpleNamespace(send_message=AsyncMock()))
        self.client.runtime.character_transition_state='RecoveryRequired'
        await self.client.tree.get_command('캐릭터').callback(interaction)
        text=str(interaction.response.send_message.await_args.kwargs['embed'].to_dict())
        self.assertIn('복구 필요',text)
        self.assertNotIn('모델 준비됨',text)

    async def test_client_views_follow_runtime_after_character_switch(self):
        from dataclasses import replace
        target=self.client.companion.hub.for_character('synthetic-character')
        backend=SimpleNamespace(character_id='synthetic-character',entry=replace(character('lime'),character_id='synthetic-character'),
            name='하루',model=True,failed=False,capabilities_verified=False,close=AsyncMock())
        self.client.runtime.backend=backend;self.client.runtime.companion=target
        self.assertIs(self.client.backend,backend)
        self.assertIs(self.client.companion,target)
        interaction=SimpleNamespace(guild_id=2,response=SimpleNamespace(send_message=AsyncMock()))
        await self.client.tree.get_command('캐릭터').callback(interaction)
        text=str(interaction.response.send_message.await_args.kwargs['embed'].to_dict())
        self.assertIn('하루',text);self.assertIn('의미 판단 검증 미완료',text)

    async def test_text_only_backend_cannot_claim_enabled_image_analysis(self):
        from echomate_bot.capabilities import public_state
        from echomate_bot.runtime import Event
        from datetime import datetime,timezone
        self.backend.supports_visual=False
        self.client.settings.set(1,'vision',True)
        event=Event(10,2,3,4,'사진 볼 수 있어?',datetime.now(timezone.utc))
        view=await public_state(self.client.runtime,event,{'view':True,'send':True})
        self.assertFalse(view['features']['vision']['implemented'])
        self.assertEqual(view['features']['vision']['state'],'unsupported')
