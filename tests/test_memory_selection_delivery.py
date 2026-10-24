"""Generated answers depend on successful empty/limited memory selections too."""
import unittest
from unittest.mock import patch
from echomate_bot.companion_store import CompanionStore
import test_bot_integration as base


class MemorySelectionDelivery(unittest.IsolatedAsyncioTestCase):
    event=base.BotIntegration.event
    settle=base.BotIntegration.settle
    asyncTearDown=base.BotIntegration.asyncTearDown

    def setUp(self):
        base.BotIntegration.setUp(self)
        self.store=self.runtime.companion=CompanionStore(self.root/'memory.sqlite3')
        self.store.set_consent(2,4,'memory',True)

    async def test_new_matching_memory_after_empty_lookup_invalidates_answer(self):
        async def text(context,cfg):
            self.store.add_memory(2,4,3,'내 취향은 귤이야')
            self.assertTrue(self.store.memories(2,4,3,'내 취향에 대해 말해 줘',allow_user_archive=True))
            return '지금 확인한 기록에는 네 취향이 없어.'
        self.backend.text=text
        await self.runtime.ingest(self.event(content='<@999> 내 취향에 대해 말해 줘'));await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_other_user_new_memory_preserves_answer(self):
        self.store.set_consent(2,5,'memory',True)
        async def text(context,cfg):
            self.store.add_memory(2,5,3,'내 취향은 귤이야')
            return '확인할 수 있는 네 취향 기록은 없어.'
        self.backend.text=text
        await self.runtime.ingest(self.event(content='<@999> 내 취향에 대해 말해 줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)

    async def test_new_ranked_row_changes_top_three_even_when_old_rows_still_valid(self):
        for i in range(3):self.store.add_memory(2,4,3,'내 취향은 과일 '+str(i))
        async def text(context,cfg):
            self.store.add_memory(2,4,3,'내 취향은 새 과일')
            return '전에 확인한 취향들만 말해 볼게.'
        self.backend.text=text
        await self.runtime.ingest(self.event(content='<@999> 내 취향에 대해 말해 줘'));await self.settle()
        self.assertFalse(self.transport.sent)

    async def test_same_user_unrelated_memory_does_not_cancel_empty_query(self):
        async def text(context,cfg):
            self.store.add_memory(2,4,3,'선호 색상은 파랑이야')
            return '이번 취향 질문에 맞는 기록은 확인되지 않아.'
        self.backend.text=text
        await self.runtime.ingest(self.event(content='<@999> 내 취향에 대해 말해 줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),1)

    async def test_sdk_original_read_new_memory_invalidates_prepared_text(self):
        from verify_utterance_gpu import Transport
        sdk=Transport();await sdk.start_sdk();original=sdk.http.get_message;inserted=[]
        async def read(channel,mid):
            result=await original(channel,mid)
            if not inserted:
                self.store.add_memory(2,4,3,'내 취향은 귤이야');inserted.append(True)
            return result
        sdk.http.get_message=read;self.runtime.transport=sdk
        event=self.event(content='<@999> 내 취향에 대해 말해 줘');sdk.register(event)
        try:
            with patch('discord.http.HTTPClient.request',side_effect=AssertionError('No live Discord')):
                await self.runtime.ingest(event);await self.settle()
            self.assertTrue(inserted);self.assertFalse(sdk.http.sends)
            self.assertEqual(self.runtime.traces[-1]['outcome'],'cancelled')
        finally:await sdk.sdk_client.close()

    async def test_unused_empty_memory_selection_does_not_cancel_reaction(self):
        self.settings.set(1,'reactions',True)
        self.backend.action='REACTION';execute=self.transport.execute
        async def changed(event,action,library,fresh):
            self.store.add_memory(2,4,3,'내 취향은 귤이야')
            return await execute(event,action,library,fresh)
        self.transport.execute=changed
        await self.runtime.ingest(self.event(content='<@999> 내 취향에 대해 말해 줘'));await self.settle()
        self.assertEqual(len(self.transport.sent),1);self.assertFalse(self.backend.calls)
