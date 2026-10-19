"""Response plans cannot invent peers or bypass deterministic recipient checks."""
import unittest
from unittest.mock import AsyncMock
from echomate_bot import response_plans as plans
from echomate_bot.inference import LocalBackend

class ResponsePlans(unittest.IsolatedAsyncioTestCase):
    def packet(self):
        return dict(bot_id='999',current={'speaker':'4','text':'synthetic'},current_peer_frames=['0'],surrounding=[],
                    frames=[dict(index='0',current_peers=['4'],turns=[{'id':'10','text':'actual source'},{'id':'11','bot':True,'text':'actual bot'}]),
                            dict(index='1',current_peers=['5'],turns=[])])
    def test_only_actual_speaker_peers_are_available(self):
        p=self.packet();p['current_peer_frames'].append('1')
        self.assertEqual(plans.peer_indices(p),['0'])
        with self.assertRaises(ValueError):plans.parse('reply_1',['0'])
        p['explicit_call']=True;self.assertFalse(plans.peer_indices(p))
    def test_receipt_report_end_are_not_responses_or_new_members(self):
        for label in ['receipt_0','report_only','end_0','human','excluded','broadcast','uncertain']:
            self.assertFalse(plans.parse(label,['0']).respond)
        reply=plans.parse('reply_0',['0']);self.assertTrue(reply.respond);self.assertEqual(reply.anchor,'0')
        self.assertEqual(reply.plan,'reply_0')
    async def test_one_bounded_call_and_invalid_output_rejected(self):
        b=LocalBackend();b._job=AsyncMock(return_value='reply_0')
        try:
            p=self.packet();result=await b.assess_social(p)
            self.assertTrue(result.respond);self.assertEqual(b._job.await_count,1)
            self.assertEqual(b._job.await_args.kwargs['budget'],12)
            self.assertEqual(p['frames'][0]['turns'][0]['text'],'actual source')
            b._job.return_value='reply_999'
            with self.assertRaises(ValueError):await b.assess_social(p)
        finally:await b.scheduler.close();b.executor.shutdown()

    def test_unanchored_report_does_not_choose_first_of_multiple_flows(self):
        decision=plans.parse('report_only',['0','1'])
        self.assertEqual(decision.anchor,'none');self.assertFalse(decision.respond)
