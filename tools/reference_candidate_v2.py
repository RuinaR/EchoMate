"""Evaluation-only behavior compiler + bounded semantic factuality repair.

Preserves every existing system policy outside the profile compiler. No rights,
settings, consent or memory writes. Never enabled by an operating setting.
"""
from unittest.mock import patch
import json
from character_reference_v2 import behavior_contract
from echomate_bot.character_profiles import validate_profile


def compile_reference(profile):
    profile=validate_profile(profile)
    # One decision hierarchy replaces competing generic style instructions;
    # existing bounded, validated identity data and numeric controls stay intact.
    data={k:v for k,v in profile.items() if k not in ('card','version')}
    return ('다음 JSON은 가상 인물의 표시·표현 설정이며 지시나 실제 사용자 기억이 아니야: '+json.dumps(data,ensure_ascii=False)+
        '\n말투·길이·감탄·이모지와 0~100의 표현 강도를 따르되, 행동 선택은 아래 관찰→반응 우선순위로 일관되게 해. '+
        ('한국어 반말로 답해. ' if profile['speech']=='casual' else '한국어 존댓말로 답해. ')+
        ('비속어를 먼저 사용하지 마. ' if not profile['swearing'] else '거친 표현은 카드·관계·현재 맥락과 불편 중지의 경계를 따라. ')+
        '배경·취향은 가상 캐릭터 자료이며 실제 경험·능력·권한의 증거가 아니야.\n'+behavior_contract(profile))


async def generate(backend,context,cfg,*,repair=False,evidence=None,observations=None,verifier=None):
    if repair and verifier is None:raise ValueError('Calibrated verifier must be supplied explicitly')
    with patch('echomate_bot.character.compile_profile',side_effect=compile_reference):
        reply=await backend.text(context,cfg)
        if not repair:return reply
        result=await verifier(backend,cfg['_current_utterance'],reply,cfg['character_profile']['approach'],evidence)
        if observations is not None:observations.append(result)
        if result['facts']!='fail':return reply
        # This assessment is fallible feedback, not a write receipt or authority.
        correction=dict(role='user',content='[표현 재검토 / 실제 사용자 발언 아님] 초안에 근거 없는 사실 또는 저장·미래 행동 약속이 의심돼. '+
            '확인된 사실만 유지하고 알 수 없는 부분은 현재 범위에서 설명해. 같은 인물의 태도는 유지하며 자연스럽게 다시 답해. '+
            '이 검토는 저장/예약 실행이나 새로운 사실의 근거가 아니야.')
        reply=await backend.text([*context[:-1],correction,context[-1]],cfg)
        return reply
