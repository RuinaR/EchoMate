import asyncio
from dataclasses import replace
import sqlite3
from types import SimpleNamespace
import unittest

import test_bot_integration as base
from test_character_runtime import Backend
from echomate_bot.character_store import CharacterStores
from echomate_bot.discord_app import EchoClient
from echomate_bot.generation_context import compile_context
from echomate_bot.identity_continuity import Feedback, Scope, Topic
from echomate_bot.identity_runtime import ChannelExperience
from echomate_bot.runtime import Runtime


class ChannelExperienceTests(unittest.IsolatedAsyncioTestCase):
    event = base.BotIntegration.event
    settle = base.BotIntegration.settle
    asyncTearDown = base.BotIntegration.asyncTearDown

    def setUp(self):
        base.BotIntegration.setUp(self)
        self.now = 1800000000
        self.path = self.root / "identity-v8.sqlite"
        self.hub = CharacterStores.create(self.path, clock=lambda: self.now)
        self.store = self.hub.for_character("lime")
        self.bridge = self.bind(self.store)
        self.backend = Backend()
        self.runtime = Runtime(
            self.settings, self.backend, self.transport, self.cache, None,
            ledger_path=self.root / "ledger.sqlite3", companion=self.store,
            channel_experience=self.bridge,
        )
        self.runtime.direct_cooldown = 0
        self.runtime.direct_spam_window = 0
        self.store.set_consent(2, 4, "memory", True)
        self.store.set_consent(2, 5, "memory", True)
        self.now += 10

    def bind(self, store):
        return ChannelExperience(store, guild=2, channel=3, topic=Topic.PROJECT)

    def source(self, number):
        return ((1800000001000 - 1420070400000) << 22) + number

    def record(self, number, *, subject=4, epoch=1, revision=1, channel=3):
        return self.bridge.record_feedback(
            Scope("lime", 2, channel, subject), source=self.source(number),
            revision=revision, epoch=epoch, topic=Topic.PROJECT, feedback=Feedback.MORE_DETAIL,
            now=self.now, expires=self.now + 50,
        )

    def seed(self):
        self.assertTrue(self.record(1))
        self.assertTrue(self.record(2))

    def project(self):
        return self.bridge.projection(self.event(), "lime")

    async def test_revoke_reopen_and_reconsent_cannot_restore_old_source(self):
        self.seed()
        self.assertIsNotNone(self.project())
        self.store.delete_personal(2, 4, "memory")
        self.now += 10
        self.bridge = self.bind(CharacterStores(self.path, clock=lambda: self.now).for_character("lime"))
        self.assertIsNone(self.project())
        self.bridge.companion.set_consent(2, 4, "memory", True)
        epoch = self.bridge.companion.consent_version(2, 4, "memory")
        self.assertFalse(self.record(2, epoch=epoch, revision=2))

    async def test_source_delete_is_durable_even_without_live_history(self):
        self.seed()
        await self.runtime.message_changed(2, 3, self.source(2), "edited source")
        self.bridge = self.bind(CharacterStores(self.path, clock=lambda: self.now).for_character("lime"))
        self.assertFalse(self.record(2, revision=3))
        self.assertIsNone(self.project())

    async def test_trigger_failure_rolls_back_both_consent_and_experience(self):
        self.seed()
        with self.store.db() as db:
            db.execute("""
                CREATE TRIGGER reject_experience_removal BEFORE DELETE ON experience
                BEGIN SELECT RAISE(ABORT, 'synthetic disk failure'); END
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.delete_personal(2, 4, "memory")
        self.assertEqual(self.store.consent_version(2, 4, "memory"), 1)
        self.assertIsNotNone(self.project())

    async def test_interleaved_users_have_distinct_flow_and_generated_strategy(self):
        self.seed()
        observed = {}
        async def generate(context, cfg):
            compiled = compile_context(self.backend.entry, "유나", context, cfg,
                                       identity_state=cfg.get("_identity_state"))
            adapted = any(part["name"] == "identity_expression" for part in compiled.sections)
            observed[cfg["_current_utterance"]] = (adapted, str(context))
            return "차근차근 설명할게." if adapted else "간단히 답할게."
        self.backend.text = generate
        a = replace(self.event(content="<@999> 종이 접기 방법 알려줘"), member_mentions=(999,))
        b = replace(self.event(id=11, content="<@999> 빵 반죽 방법 알려줘"), author=5, member_mentions=(999,))
        self.settings.set_scope(1, 2, 8, "mention", thread=True)
        await self.runtime.ingest(replace(b, id=12, channel=8, parent=3))
        await self.runtime.ingest(a)
        await self.runtime.ingest(b)
        await self.settle()
        self.assertTrue(observed[a.content][0])
        self.assertFalse(observed[b.content][0])
        self.assertNotIn("빵 반죽", observed[a.content][1])
        self.assertNotIn("종이 접기", observed[b.content][1])
        self.assertEqual({e.response_to or e.id: action.text for e, action in self.transport.sent},
                         {10: "차근차근 설명할게.", 11: "간단히 답할게."})
        self.assertEqual(len({e.conversation_id for e, _ in self.transport.sent}), 2)
        self.assertFalse(self.record(3, channel=8))

    async def test_consent_changes_after_generation_before_transport(self):
        self.seed()
        original = self.transport.execute
        async def revoke_then_execute(event, action, library, fresh):
            self.store.set_consent(2, 4, "memory", False)
            return await original(event, action, library, fresh)
        self.transport.execute = revoke_then_execute
        await self.runtime.ingest(replace(self.event(), member_mentions=(999,)))
        await self.settle()
        self.assertTrue(self.backend.calls)
        self.assertFalse(self.transport.sent)

    async def test_character_epoch_changes_at_send(self):
        self.seed()
        original = self.transport.execute
        async def switch_then_execute(event, action, library, fresh):
            self.runtime.model_generation_epoch += 1
            return await original(event, action, library, fresh)
        self.transport.execute = switch_then_execute
        await self.runtime.ingest(replace(self.event(), member_mentions=(999,)))
        await self.settle()
        self.assertTrue(self.backend.calls)
        self.assertFalse(self.transport.sent)

    async def test_experience_source_deleted_during_generation(self):
        self.seed()
        entered = asyncio.Event()
        release = asyncio.Event()
        async def generate(context, cfg):
            self.assertIn("_identity_state", cfg)
            entered.set()
            await release.wait()
            return "출처가 바뀐 표현 전략으로 생성한 합성 답변"
        self.backend.text = generate
        await self.runtime.ingest(replace(self.event(), member_mentions=(999,)))
        try:
            await asyncio.wait_for(entered.wait(), 3)
            await self.runtime.message_changed(2, 3, self.source(1))
        finally:
            release.set()
        await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_bulk_gateway_handler_is_scoped_and_durable(self):
        self.seed()
        client = SimpleNamespace(runtime=self.runtime)
        payload = SimpleNamespace(guild_id=2, channel_id=8, message_ids={self.source(1), self.source(2)})
        await EchoClient.on_raw_bulk_message_delete(client, payload)
        self.assertIsNotNone(self.project())
        payload.channel_id = 3
        await EchoClient.on_raw_bulk_message_delete(client, payload)
        self.assertIsNone(self.project())
        self.assertFalse(self.record(1, revision=2))
        self.assertFalse(self.record(2, revision=2))

    async def test_failed_source_removal_stops_live_runtime(self):
        self.seed()
        with self.store.db() as db:
            db.execute("""
                CREATE TRIGGER reject_source_removal BEFORE DELETE ON experience
                BEGIN SELECT RAISE(ABORT, 'synthetic write failure'); END
            """)
        await self.runtime.message_changed(2, 3, self.source(1))
        self.assertTrue(self.runtime.stopped)
        await self.runtime.ingest(self.event())
        await self.settle()
        self.assertFalse(self.transport.sent)
