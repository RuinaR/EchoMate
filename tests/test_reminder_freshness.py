"""Aggregate scheduler races, isolated SQLite; no live Discord."""
import unittest
from unittest.mock import AsyncMock,patch
import test_bot_integration as base
from echomate_bot.companion_store import CompanionStore


class ReminderFreshness(unittest.IsolatedAsyncioTestCase):
    event=base.BotIntegration.event
    asyncTearDown=base.BotIntegration.asyncTearDown

    def setUp(self):
        base.BotIntegration.setUp(self)
        self.store=self.runtime.companion=CompanionStore(self.root/'companion.sqlite3')
        self.now=self.store.clock()
        self.row=self.store.reserve_reminder(self.event(),self.now+1,'UTC','합성 알림')
        self.current=self.now+2
        self.store.clock=lambda:self.current

    async def test_pause_during_preflight_does_not_claim_or_send(self):
        permissions=self.transport.permissions
        async def pause(event):
            self.settings.set(1,'enabled',False)
            return await permissions(event)
        self.transport.permissions=pause
        self.transport.deliver_reminder=AsyncMock()
        await self.runtime.deliver_reminders()
        self.transport.deliver_reminder.assert_not_awaited()
        self.assertEqual(self.store.reminders(2,4)[0]['status'],'scheduled')

    async def test_model_switch_pauses_due_reminder_without_claim(self):
        self.runtime.changing_model=True
        self.transport.deliver_reminder=AsyncMock()
        await self.runtime.deliver_reminders()
        self.transport.deliver_reminder.assert_not_awaited()
        self.assertEqual(self.store.reminders(2,4)[0]['status'],'scheduled')

    async def test_completed_switch_during_permissions_invalidates_old_delivery(self):
        permissions=self.transport.permissions
        async def switched(event):
            self.runtime.model_generation_epoch+=1
            self.runtime.changing_model=False
            return await permissions(event)
        self.transport.permissions=switched
        self.transport.deliver_reminder=AsyncMock()
        await self.runtime.deliver_reminders()
        self.transport.deliver_reminder.assert_not_awaited()
        self.assertEqual(self.store.reminders(2,4)[0]['status'],'scheduled')

    async def test_pause_after_claim_blocks_last_delivery_check(self):
        delivered=[]
        async def send(row,fresh):
            self.settings.set(1,'enabled',False)
            if not await fresh():raise ValueError('Superseded before SDK send')
            delivered.append(row)
        self.transport.deliver_reminder=send
        await self.runtime.deliver_reminders()
        self.assertFalse(delivered)
        self.assertEqual(self.store.reminders(2,4)[0]['status'],'failed')
        await self.runtime.deliver_reminders()
        self.assertFalse(delivered)

    async def test_deadline_crossed_during_permissions_is_not_delivered(self):
        permissions=self.transport.permissions
        async def late(event):
            self.current=self.row['due_at']+self.settings.get()['reminder_grace']+1
            return await permissions(event)
        self.transport.permissions=late
        self.transport.deliver_reminder=AsyncMock()
        await self.runtime.deliver_reminders()
        self.transport.deliver_reminder.assert_not_awaited()

    async def test_unchanged_due_row_is_delivered_once(self):
        delivered=[]
        async def send(row,fresh):
            self.assertTrue(await fresh());delivered.append(row)
        self.transport.deliver_reminder=send
        await self.runtime.deliver_reminders();await self.runtime.deliver_reminders()
        self.assertEqual(len(delivered),1)
        self.assertEqual(self.store.reminders(2,4)[0]['status'],'delivered')

    async def test_real_sdk_final_permission_deadline_blocks_http_send(self):
        from verify_utterance_gpu import Transport
        sdk=Transport();await sdk.start_sdk()
        client=sdk.sdk_client;client._ready.set()
        channel=client.get_channel(3)
        client.fetch_channel=AsyncMock(return_value=channel)
        original=sdk.http.get_member;member_checked=[]
        async def member(guild,user):
            member_checked.append(True);return await original(guild,user)
        sdk.http.get_member=member
        permissions=self.transport.permissions
        async def late(event):
            if member_checked:self.current=self.row['due_at']+self.settings.get()['reminder_grace']+1
            return await permissions(event)
        self.transport.permissions=late
        self.transport.deliver_reminder=sdk.sdk.deliver_reminder
        try:
            with patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')):
                await self.runtime.deliver_reminders()
            self.assertFalse(sdk.http.sends)
            self.assertEqual(self.store.reminders(2,4)[0]['status'],'failed')
        finally:await client.close()

    async def test_changed_grace_during_permission_check_is_revalidated(self):
        self.current=self.row['due_at']+120
        permissions=self.transport.permissions
        async def shortened(event):
            self.settings.set(1,'reminder_grace',60)
            return await permissions(event)
        self.transport.permissions=shortened
        self.transport.deliver_reminder=AsyncMock()
        await self.runtime.deliver_reminders()
        self.transport.deliver_reminder.assert_not_awaited()

    async def test_deadline_during_processing_read_is_rechecked_without_await(self):
        processing=self.store.processing;delivered=[]
        def late(key):
            value=processing(key)
            self.current=self.row['due_at']+self.settings.get()['reminder_grace']+1
            return value
        self.store.processing=late
        async def send(row,fresh):
            if not await fresh():raise ValueError('Expired before send')
            delivered.append(row)
        self.transport.deliver_reminder=send
        await self.runtime.deliver_reminders()
        self.assertFalse(delivered)
