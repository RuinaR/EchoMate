"""Confirmed audience and optional relation are separate bounded contracts."""
import json
import unittest
from unittest.mock import AsyncMock

from echomate_bot.inference import LocalBackend


class DirectRelation(unittest.IsolatedAsyncioTestCase):
    async def test_only_confirmed_peer_frames_can_be_returned(self):
        backend=LocalBackend();backend._job=AsyncMock(return_value='continue 1')
        try:
            packet=dict(current={'speaker':'4','text':'합성 질문'},current_peer_frames=['1'],surrounding=[],
                        frames=[dict(index='0',turns=[{'text':'unrelated-private-frame'}]),dict(index='1',turns=[{'text':'synthetic scoped reply'}])])
            self.assertEqual(await backend.link_direct(packet),'1')
            call=backend._job.await_args
            self.assertEqual(call.kwargs['choices'],['new','continue 1'])
            self.assertNotIn('unrelated-private-frame',json.dumps(call.args[0]))
            self.assertEqual(packet['frames'][0]['turns'][0]['text'],'unrelated-private-frame')
            backend._job.return_value='continue 0'
            with self.assertRaises(ValueError):await backend.link_direct(packet)
        finally:
            await backend.scheduler.close();backend.executor.shutdown()

    async def test_no_peer_evidence_does_not_invoke_gpu(self):
        backend=LocalBackend();backend._job=AsyncMock()
        try:
            self.assertEqual(await backend.link_direct(dict(current={},frames=[],current_peer_frames=[])),'none')
            backend._job.assert_not_awaited()
        finally:
            await backend.scheduler.close();backend.executor.shutdown()

    async def test_application_reference_indices_are_bounded_without_claiming_peer_identity(self):
        backend=LocalBackend();backend._job=AsyncMock(return_value='continue 0')
        try:
            packet=dict(current={'speaker':'5','text':'synthetic reference'},current_peer_frames=[],direct_reference_frames=['0'],
                        frames=[dict(index='0',turns=[{'speaker':'4','text':'actual source'}])],surrounding=[])
            self.assertEqual(await backend.link_direct(packet),'0')
            self.assertEqual(packet['current_peer_frames'],[])
            self.assertEqual(backend._job.await_args.kwargs['choices'],['new','continue 0'])
        finally:await backend.scheduler.close();backend.executor.shutdown()
