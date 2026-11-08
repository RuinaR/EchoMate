import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import discord

import test_bot_integration as base
from test_character_runtime import Backend
from echomate_bot.character_store import CharacterStores
from echomate_bot.discord_app import DiscordTransport, EchoClient
from echomate_bot.generation_context import compile_context
from echomate_bot.identity_continuity import Feedback, Scope, Topic
from echomate_bot.identity_runtime import ChannelExperience, SourceObservation, SourceStatus, content_digest
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
        self.store.set_consent(2, 4, "adaptation", True)
        self.store.set_consent(2, 5, "adaptation", True)
        self.now += 10

    def bind(self, store):
        return ChannelExperience(store, guild=2, channel=3, topic=Topic.PROJECT)

    def source(self, number):
        return ((1800000001000 - 1420070400000) << 22) + number

    def record(self, number, *, subject=4, epoch=1, revision=1, channel=3):
        return self.bridge.record_feedback(
            Scope("lime", 2, channel, subject), source=self.source(number),
            revision=revision, epoch=epoch, topic=Topic.PROJECT, feedback=Feedback.MORE_DETAIL,
            now=self.now, expires=self.now + 50, digest=content_digest("synthetic feedback"),
        )

    def seed(self):
        self.assertTrue(self.record(1))
        self.assertTrue(self.record(2))

    def project(self):
        return self.bridge.projection(self.event(), "lime")

    def sdk_transport(self):
        guild = SimpleNamespace(id=2,me=object())
        channel = Mock(spec=discord.TextChannel)
        channel.id=3;channel.guild=guild
        channel.permissions_for.return_value=SimpleNamespace(view_channel=True,read_message_history=True)
        channel.fetch_message=AsyncMock()
        guild.get_channel=lambda cid:channel if cid==3 else None
        client=SimpleNamespace(runtime=self.runtime,settings=self.settings,is_ready=lambda:True,
                               get_guild=lambda gid:guild if gid==2 else None)
        self.transport.experience_source=DiscordTransport(client).experience_source
        return channel

    def sdk_message(self, channel, source, *, author=4, content="synthetic feedback", edited=False):
        return SimpleNamespace(id=source,guild=channel.guild,channel=channel,
                               author=SimpleNamespace(id=author,bot=False),webhook_id=None,
                               created_at=datetime.fromtimestamp(1800000001,timezone.utc),
                               edited_at=datetime.fromtimestamp(1800000002,timezone.utc) if edited else None,
                               content=content)

    async def test_sdk_reconciliation_proves_identity_revision_and_content(self):
        revision=1800000001000000
        for source in (1,2):self.assertTrue(self.record(source,revision=revision))
        self.runtime.pause_gateway()
        await self.runtime.resume_gateway()
        channel=self.sdk_transport()
        channel.fetch_message.side_effect=lambda source:self.sdk_message(channel,source,author=5)
        self.assertEqual(await self.runtime.verify_experience_sources(4),1)
        self.assertIsNone(self.project())
        self.assertEqual(self.bridge.verification_status()["last_result"],"unavailable")
        channel.fetch_message.side_effect=lambda source:self.sdk_message(channel,source)
        self.assertEqual(await self.runtime.verify_experience_sources(4),2)
        self.assertIsNotNone(self.project())
        self.bridge.quarantine()
        channel.fetch_message.side_effect=lambda source:self.sdk_message(channel,source,content="ambiguous content")
        self.assertEqual(await self.runtime.verify_experience_sources(4),1)
        self.assertEqual(self.bridge.verification_status()["last_result"],"unavailable")
        self.assertIsNone(self.project())
        channel.fetch_message.side_effect=lambda source:self.sdk_message(
            channel,source,content="changed content" if source==self.source(2) else "synthetic feedback",
            edited=source==self.source(2))
        self.assertEqual(await self.runtime.verify_experience_sources(4),2)
        self.assertEqual(self.bridge.verification_status()["last_result"],"changed")
        self.assertIsNone(self.project())

    async def test_sdk_separates_failures_and_only_unknown_message_removes_source(self):
        self.seed()
        self.bridge.quarantine()
        channel=self.sdk_transport()
        errors=(
            (discord.Forbidden(SimpleNamespace(status=403,reason="Forbidden"),{"code":50013}),"forbidden"),
            (discord.NotFound(SimpleNamespace(status=404,reason="Not found"),{"code":10003}),"unavailable"),
            (discord.HTTPException(SimpleNamespace(status=429,reason="Limited"),{"code":0}),"rate_limited"),
            (OSError("synthetic disconnect"),"network_failure"),
        )
        scope=Scope("lime",2,3,4)
        for exc,status in errors:
            channel.fetch_message.side_effect=exc
            self.assertEqual(await self.runtime.verify_experience_sources(4),1)
            self.assertEqual(self.bridge.verification_status()["last_result"],status)
            self.assertEqual(self.bridge.state(scope,epoch=1,topic=Topic.PROJECT,now=self.now).count,2)
            self.assertIsNone(self.project())
        channel.fetch_message.side_effect=discord.NotFound(
            SimpleNamespace(status=404,reason="Not found"),{"code":10008})
        self.assertEqual(await self.runtime.verify_experience_sources(4),2)
        self.assertEqual(self.bridge.verification_status()["last_result"],"deleted")
        self.assertFalse(self.record(1,revision=2))

    async def test_sdk_inflight_consent_channel_and_storage_invalidate_results(self):
        self.seed()
        self.bridge.quarantine()
        channel=self.sdk_transport()
        async def change(source):
            self.settings.select_operating_channel(1,2,6,"mention","silent")
            return self.sdk_message(channel,source)
        channel.fetch_message.side_effect=change
        self.assertEqual(await self.runtime.verify_experience_sources(4),1)
        self.assertEqual(self.bridge.verification_status()["last_result"],"stale")
        self.assertIsNone(self.project())
        self.settings.select_operating_channel(1,2,3,"mention","silent")
        async def revoke(source):
            self.store.set_consent(2,4,"adaptation",False)
            return self.sdk_message(channel,source)
        channel.fetch_message.side_effect=revoke
        self.assertEqual(await self.runtime.verify_experience_sources(4),1)
        self.assertEqual(self.bridge.verification_status()["last_result"],"stale")
        self.assertIsNone(self.project())
        with patch.object(self.store,"consent_version",side_effect=sqlite3.OperationalError):
            self.assertEqual(await self.runtime.verify_experience_sources(4),0)
        self.assertEqual(self.bridge.verification_status()["last_result"],"storage_failure")

    async def test_memory_consent_is_independent_and_legacy_rows_are_quarantined(self):
        self.store.set_consent(2,4,"memory",True)
        self.store.set_consent(2,4,"adaptation",False)
        self.assertFalse(self.record(1))
        self.assertTrue(self.store.consent(2,4)["memory"])
        self.store.set_consent(2,4,"adaptation",True)
        self.assertFalse(self.record(1,epoch=3))
        # Legacy provenance has no content digest and cannot be verified.
        self.now=1800000000
        self.store.set_consent(2,4,"adaptation",True)
        self.now+=10
        scope=Scope("lime",2,3,4)
        with self.store.db() as db:
            db.execute("INSERT INTO experience VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (*scope.key(),self.source(1),1,4,"project","more_detail",self.now+10))
        channel=self.sdk_transport()
        self.assertEqual(await self.runtime.verify_experience_sources(4),0)
        channel.fetch_message.assert_not_awaited()
        self.assertEqual(self.bridge.verification_status()["last_result"],"unavailable")
        self.assertIsNone(self.project())

    async def test_saved_rows_cannot_override_current_revocation(self):
        self.seed()
        with self.store.db() as db:
            saved=[tuple(row) for row in db.execute("SELECT * FROM experience")]
            evidence=[tuple(row) for row in db.execute("SELECT * FROM experience_evidence")]
        self.store.set_consent(2,4,"adaptation",False)
        # Deliberately simulate stale rows supplied by a proposed import,
        # without restoring the older consent authority.
        with self.store.db() as db:
            db.executemany("INSERT INTO experience VALUES(?,?,?,?,?,?,?,?,?,?)",saved)
            db.executemany("INSERT INTO experience_evidence VALUES(?,?,?,?,?,?,?)",evidence)
        self.bridge.quarantine()
        channel=self.sdk_transport()
        self.assertEqual(await self.runtime.verify_experience_sources(4),0)
        channel.fetch_message.assert_not_awaited()
        self.assertIsNone(self.project())

    async def test_sdk_character_change_and_concurrent_verification(self):
        self.seed()
        self.bridge.quarantine()
        channel=self.sdk_transport()
        entered=asyncio.Event()
        release=asyncio.Event()
        async def fetch(source):
            entered.set()
            await release.wait()
            return self.sdk_message(channel,source)
        channel.fetch_message.side_effect=fetch
        pending=asyncio.create_task(self.runtime.verify_experience_sources(4))
        try:
            await asyncio.wait_for(entered.wait(),3)
            self.assertEqual(await self.runtime.verify_experience_sources(5),0)
            self.runtime.model_generation_epoch+=1
        finally:
            release.set()
        self.assertEqual(await pending,1)
        self.assertEqual(channel.fetch_message.await_count,1)
        self.assertEqual(self.bridge.verification_status()["last_result"],"stale")

    async def test_revoke_reopen_and_reconsent_cannot_restore_old_source(self):
        self.seed()
        self.assertIsNotNone(self.project())
        self.store.delete_personal(2, 4, "adaptation")
        self.now += 10
        self.bridge = self.bind(CharacterStores(self.path, clock=lambda: self.now).for_character("lime"))
        self.assertIsNone(self.project())
        self.bridge.companion.set_consent(2, 4, "adaptation", True)
        epoch = self.bridge.companion.consent_version(2, 4, "adaptation")
        self.assertFalse(self.record(2, epoch=epoch, revision=2))

    async def test_source_delete_is_durable_even_without_live_history(self):
        self.seed()
        await self.runtime.message_changed(2, 3, self.source(2), "edited source")
        self.bridge = self.bind(CharacterStores(self.path, clock=lambda: self.now).for_character("lime"))
        self.assertFalse(self.record(2, revision=3))
        self.assertIsNone(self.project())

    async def test_restart_quarantines_until_all_sources_are_checked(self):
        self.seed()
        self.bridge = self.bind(CharacterStores(self.path, clock=lambda: self.now).for_character("lime"))
        scope = Scope("lime", 2, 3, 4)
        self.assertIsNone(self.project())
        async def verified(key, source):
            return SourceObservation(SourceStatus.FOUND, key, source, 1, content_digest("synthetic feedback"))
        self.assertEqual(await self.bridge.reconcile(scope, epoch=1, fetch_source=verified, limit=1), 1)
        self.assertIsNone(self.project())
        self.assertEqual(await self.bridge.reconcile(scope, epoch=1, fetch_source=verified), 1)
        self.assertIsNotNone(self.project())

    async def test_reconnect_does_not_treat_unavailable_as_deleted(self):
        self.seed()
        self.runtime.pause_gateway()
        await self.runtime.resume_gateway()
        scope = Scope("lime", 2, 3, 4)
        async def unavailable(key, source):
            return SourceObservation(SourceStatus.UNAVAILABLE, key, source)
        self.assertEqual(await self.bridge.reconcile(scope, epoch=1, fetch_source=unavailable), 1)
        self.assertIsNone(self.project())
        self.assertEqual(self.bridge.state(scope, epoch=1, topic=Topic.PROJECT, now=self.now).count, 2)
        async def changed(key, source):
            return SourceObservation(SourceStatus.DELETED if source == self.source(1) else SourceStatus.FOUND,
                                     key, source, 2, content_digest("edited feedback"))
        self.assertEqual(await self.bridge.reconcile(scope, epoch=1, fetch_source=changed), 2)
        self.assertEqual(self.bridge.state(scope, epoch=1, topic=Topic.PROJECT, now=self.now).count, 0)
        self.assertFalse(self.record(1, revision=3))

    async def test_disconnect_during_verification_rejects_late_result(self):
        self.seed()
        self.bridge.quarantine()
        async def stale(key, source):
            self.bridge.quarantine()
            return SourceObservation(SourceStatus.FOUND, key, source, 1, content_digest("synthetic feedback"))
        scope = Scope("lime", 2, 3, 4)
        self.assertEqual(await self.bridge.reconcile(scope, epoch=1, fetch_source=stale), 1)
        self.assertEqual(self.bridge.verification_status()["session_marks"], 0)

    async def test_signed_channel_change_blocks_an_old_send_and_thread(self):
        self.settings.select_operating_channel(1, 2, 3, "mention", "silent")
        self.settings.set_scope(1, 2, 8, "mention", thread=True)
        self.backend.wait = asyncio.Event()
        await self.runtime.ingest(replace(self.event(), member_mentions=(999,)))
        for _ in range(100):
            if self.backend.calls:break
            await asyncio.sleep(.01)
        self.assertTrue(self.backend.calls)
        before = self.runtime.reset_preview(2, 3)
        self.assertEqual((before["conversations"], before["pending"]), (1, 1))
        self.assertEqual(self.runtime.reset_preview(2, 3), before)
        self.settings.select_operating_channel(1, 2, 6, "mention", "silent")
        self.backend.wait.set()
        await self.settle()
        self.assertFalse(self.transport.sent)
        from echomate_bot.settings import Settings, scope
        reloaded = Settings(1, self.settings._key.decode(), self.settings.path).get()
        self.assertEqual(reloaded["operating_channel"], [2, 6])
        self.assertEqual(scope(reloaded, 2, 6), "mention")
        self.assertEqual(scope(reloaded, 2, 3), "silent")
        self.assertEqual(scope(reloaded, 2, 8, 6), "silent")

    async def test_trigger_failure_rolls_back_both_consent_and_experience(self):
        self.seed()
        with self.store.db() as db:
            db.execute("""
                CREATE TRIGGER reject_experience_removal BEFORE DELETE ON experience
                BEGIN SELECT RAISE(ABORT, 'synthetic disk failure'); END
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.delete_personal(2, 4, "adaptation")
        self.assertEqual(self.store.consent_version(2, 4, "adaptation"), 1)
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
            self.store.set_consent(2, 4, "adaptation", False)
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
