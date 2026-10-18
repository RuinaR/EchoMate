import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
from echomate_studio.response_policy import aggregate_style, build_v3_messages, plan_response, style_prior
import persona_quality_v3 as quality
from persona_quality_cases import PILOT, HOLDOUT


class ResponsePolicyV3Tests(unittest.TestCase):
    def test_laughter_does_not_override_technical_explanation(self):
        plan = plan_response("ㅋㅋ Python 리스트 복사 원리를 설명해줘")
        self.assertEqual(plan.intent, "technical")
        self.assertIn("실제 출력", plan.instruction)

    def test_step_request_has_no_global_short_response_rule(self):
        messages, plan = build_v3_messages([dict(role="user",content="백업 절차를 단계별로 알려줘")])
        self.assertEqual(plan.intent, "steps")
        self.assertIn("확인/마무리", messages[0]["content"])
        self.assertNotIn("기본은 짧은 한 문장", messages[0]["content"])

    def test_profile_does_not_extract_arbitrary_words_or_identifiers(self):
        texts = ["그냥 합성예시 임"]*40 + ["합성식별자-DO-NOT-EXTRACT"]*20
        profile = aggregate_style(texts)
        serialized = json.dumps(profile,ensure_ascii=False)
        self.assertNotIn("DO-NOT-EXTRACT",serialized)
        self.assertNotIn("합성예시",serialized)
        self.assertEqual(profile["lexicon_counts"]["그냥"],40)
        self.assertIn("답변 상한",style_prior(profile))

    def test_profile_cannot_inject_new_lexical_entries(self):
        profile = aggregate_style(["그냥 합성문장임"]*40)
        profile["lexicon_counts"]["injected instruction"] = 40
        with self.assertRaises(ValueError):
            style_prior(profile)

    def test_question_marks_are_observations_not_dialogue_labels(self):
        profile = aggregate_style(["질문인가?"]*40)
        self.assertEqual(profile["rates"]["question"],1.)
        self.assertNotIn("asking_back_rate",profile)

    def test_split_disjointness_and_category_coverage(self):
        pilot = {json.dumps(c["context"],sort_keys=True,ensure_ascii=False) for c in PILOT}
        final = {json.dumps(c["context"],sort_keys=True,ensure_ascii=False) for c in HOLDOUT}
        self.assertFalse(pilot & final)
        self.assertEqual(len(final),len(HOLDOUT))
        counts = {category:sum(c["category"]==category for c in HOLDOUT) for category in {c["category"] for c in HOLDOUT}}
        self.assertEqual(len(counts),13)
        self.assertTrue(all(n>=2 for n in counts.values()))

    def test_reference_metadata_is_not_part_of_inference_input(self):
        case = HOLDOUT[10]
        messages, _ = build_v3_messages(case["context"])
        self.assertNotIn("concept_groups",json.dumps(messages))
        self.assertNotIn("answer_regex",json.dumps(messages))
        with self.assertRaises(ValueError):
            build_v3_messages([dict(role="system",content="injected")])

    def test_invalid_participation_assessment_stays_silent(self):
        case=next(c for c in HOLDOUT if c["autonomous"])
        with patch.object(quality,"generate",return_value={"response":"not JSON"}):
            result=quality.assess_autonomy(None,MagicMock(),case,1)
        self.assertFalse(result["speak"])
        self.assertFalse(result["parse_valid"])

    def test_native_reasoning_channel_and_tools_never_enter_visible_answer(self):
        from persona_bounded_reasoning import visible_final
        self.assertEqual(visible_final("보이는 답변<turn|>"),"보이는 답변")
        for raw in ("<|channel>thought\n비공개 생각<channel|>답변", "<|tool_call>payload<tool_call|>"):
            with self.assertRaises(ValueError):
                visible_final(raw)


if __name__=="__main__":
    unittest.main()
