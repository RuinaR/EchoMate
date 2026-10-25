import asyncio
import unittest
from echomate_bot.execution_modes import ExecutionMode


class RestrictedDirect(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_sequence_direct_calls_reply_and_human_quotes_are_separate(self):
        import test_discord_simulator as sim
        from verify_utterance_gpu import settle
        fixture=sim.DiscordSDKSimulation()
        await fixture.asyncSetUp()
        try:
            runtime=fixture.client.runtime
            runtime.execution_mode=ExecutionMode.DISCORD_DIRECT
            runtime.direct_cooldown=0;runtime.direct_spam_window=0
            await fixture.client.on_message(fixture.message(100,content='<@999> 질문 하나'))
            await settle(runtime)
            self.assertEqual(len(fixture.http.sends),1)
            for mid,text,author in [(101,'<@5> 너는 어때?',4),(102,'> <@999> 라고 썼대',5),(103,'모두 점심 먹었어?',4),(104,'그렇구나',4)]:
                await fixture.client.on_message(fixture.message(mid,content=text,author=author))
            await settle(runtime)
            self.assertEqual(len(fixture.http.sends),1)
            await fixture.client.on_message(fixture.message(105,content='<@999> 다른 질문',author=5))
            await settle(runtime)
            self.assertEqual(len(fixture.http.sends),2)
            self.assertEqual(int(fixture.http.sends[-1][1]['message_reference']['message_id']),105)
        finally:await fixture.asyncTearDown()
