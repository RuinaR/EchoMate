from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from echomate_bot.character_models import character
from echomate_bot.generation_context import compile_context
from echomate_bot.identity_continuity import ExperienceJournal, Feedback, Scope, State, Topic


class IdentityContinuityTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "identity.sqlite"
        self.epochs = {101: 1, 102: 1}
        self.scope = Scope("lime", 1, 10, 101)
        self.journal = self.reopen()

    def reopen(self):
        return ExperienceJournal(
            self.path, authorize=lambda scope, epoch: self.epochs.get(scope.subject) == epoch
        )

    def record(self, source, feedback=Feedback.BRIEFER, *, scope=None, revision=1,
               epoch=1, topic=Topic.PROJECT, expires=100):
        return self.journal.record_feedback(
            scope or self.scope, source=source, revision=revision, epoch=epoch,
            topic=topic, feedback=feedback, now=10, expires=expires,
        )

    def state(self, *, scope=None, epoch=1, topic=Topic.PROJECT, now=11):
        return self.journal.state(scope or self.scope, epoch=epoch, topic=topic, now=now)

    def test_replay_duplicate_and_restart(self):
        for source in (3, 1, 2):
            self.assertTrue(self.record(source))
        self.assertFalse(self.record(2, Feedback.MORE_DETAIL))
        expected = State(3, -4, 2, -1, 3, 1)
        self.assertEqual(self.state(), expected)
        self.journal = self.reopen()
        self.assertEqual(self.state(), expected)

    def test_edit_delete_and_expiry_rebuild_both_state_and_rule(self):
        self.record(1)
        self.record(2)
        self.record(3, expires=12)
        self.assertTrue(self.record(1, Feedback.MORE_DETAIL, revision=2))
        self.assertEqual((self.state().detail, self.state().step), (-1, 2))
        self.journal.invalidate_source(self.scope, source=2, revision=2, epoch=1)
        self.assertFalse(self.record(2, revision=2))
        self.assertEqual((self.state().detail, self.state().step), (0, 1))
        self.assertEqual(self.state(now=12), State(1, 1, 1, 1, 1, 2))

    def test_revocation_across_channels_and_characters_preserves_other_subject(self):
        other_channel = Scope("lime", 1, 11, 101)
        other_character = Scope("other", 1, 10, 101)
        other_subject = Scope("lime", 1, 10, 102)
        for scope in (self.scope, other_channel, other_character, other_subject):
            self.record(1, scope=scope)
        self.journal.revoke(guild=1, subject=101, epoch=1)
        self.journal = self.reopen()
        for scope in (self.scope, other_channel, other_character):
            self.assertEqual(self.state(scope=scope), State())
            self.assertFalse(self.record(2, scope=scope))
        self.assertEqual(self.state(scope=other_subject).count, 1)
        self.epochs[101] = 2
        self.assertEqual(self.state(epoch=2), State())
        self.assertTrue(self.record(3, epoch=2))
        self.journal.revoke(guild=1, subject=101, epoch=1)
        self.assertEqual(self.state(epoch=2).count, 1)

    def test_failure_rolls_back_revocation(self):
        self.record(1)
        with sqlite3.connect(self.path) as db:
            db.execute("""
                CREATE TRIGGER fail_delete BEFORE DELETE ON experience
                BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.journal.revoke(guild=1, subject=101, epoch=1)
        self.journal = self.reopen()
        self.assertEqual(self.state().count, 1)

    def test_invalid_and_unauthorized_input(self):
        with self.assertRaises(ValueError):
            self.record(1, "generated suggestion")
        self.assertFalse(self.record(1, epoch=2))
        self.record(1)
        self.epochs.clear()
        self.assertEqual(self.state(), State())

    def test_deleted_source_cannot_be_reintroduced_by_delayed_edit(self):
        self.record(1)
        self.journal.invalidate_source(self.scope, source=1, revision=1, epoch=1, deleted=True)
        self.journal = self.reopen()
        self.assertFalse(self.record(1, revision=5))
        self.assertEqual(self.state(), State())

    def test_reversal_does_not_inherit_previous_direction_acceleration(self):
        for source, feedback in enumerate(
            [Feedback.BRIEFER] * 3 + [Feedback.MORE_DETAIL], 1
        ):
            self.record(source, feedback)
        self.assertEqual((self.state().detail, self.state().step), (-3, 1))

    def test_rejects_foreign_database(self):
        foreign = self.path.with_name("foreign.sqlite")
        with sqlite3.connect(foreign) as db:
            db.execute("CREATE TABLE unrelated (x)")
            db.execute("PRAGMA user_version=1")
        with self.assertRaises(ValueError):
            ExperienceJournal(foreign, authorize=lambda *_: True)

    def test_synthetic_context_comparison(self):
        messages = [{"role": "user", "content": "다음 단계가 궁금해."}]

        def compile_view(state=None):
            return compile_context(character("lime"), "라임", messages, {}, identity_state=state)

        baseline = compile_view()
        self.assertEqual(compile_view(self.state()), baseline)
        for source in range(1, 5):
            self.record(source, Feedback.MORE_DETAIL)
        self.assertEqual(self.state().detail, 6)  # Fixed-step ablation would be 4.
        adapted = compile_view(self.state())
        style = [part for part in adapted.sections if part["authority"] == "STYLE"]
        self.assertEqual(len(style), 1)
        self.assertIn("자세히", style[0]["content"])
        self.assertEqual(tuple(p for p in adapted.sections if p not in style), baseline.sections)
        self.assertEqual(adapted.messages[1:], baseline.messages[1:])
        for scope in (Scope("lime", 2, 10, 101), Scope("lime", 1, 12, 101),
                      Scope("lime", 1, 10, 102), Scope("other", 1, 10, 101)):
            self.assertEqual(compile_view(self.state(scope=scope)), baseline)
        self.assertEqual(compile_view(self.state(topic=Topic.LEARNING)), baseline)
        self.journal.revoke(guild=1, subject=101, epoch=1)
        self.assertEqual(compile_view(self.state()), baseline)
