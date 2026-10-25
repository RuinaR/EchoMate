"""Execution capability boundaries; a local success is no social certificate."""
from enum import Enum
from dataclasses import dataclass


class ExecutionMode(str, Enum):
    LOCAL_CHAT='LOCAL_CHAT'
    DISCORD_DIRECT='DISCORD_DIRECT'
    DISCORD_AUTONOMOUS='DISCORD_AUTONOMOUS'


def local_ready(technical, identity):
    return bool(technical and identity)


def structural_direct_reason(event,bot_id,*,verified_reply=False):
    """No name/semantic/autonomy vote can create restricted-beta eligibility."""
    from .social import direct_signal
    if event.reply_to is not None and (event.reply_author==bot_id or verified_reply):return 'bot_reply'
    if bot_id in event.member_mentions and direct_signal(event,bot_id,'none'):return 'bot_mention'
    return None


class GateStatus(str,Enum):
    PASS='PASS'
    FAIL='FAIL'
    BLOCKED='BLOCKED'
    NOT_VERIFIED='NOT VERIFIED'
    DEFERRED='DEFERRED'
    NOT_APPLICABLE='NOT APPLICABLE'


class Risk(str,Enum):
    SAFETY='SAFETY'
    HIGH_RISK_FACTUALITY='HIGH_RISK_FACTUALITY'
    QUALITY='QUALITY'


ALL=frozenset(ExecutionMode)
DISCORD=ALL-{ExecutionMode.LOCAL_CHAT}
AUTO=frozenset({ExecutionMode.DISCORD_AUTONOMOUS})


@dataclass(frozen=True)
class GateRule:
    key:str
    risk:Risk
    modes:frozenset
    required:frozenset
    impact:str
    verification:str
    user_check:str
    live_only:bool=False


RULES=(
    GateRule('technical',Risk.SAFETY,ALL,ALL,'모델·이름·자원 안전','실제 GPU·취소/해제','설치·이름·로딩·취소'),
    GateRule('privacy',Risk.SAFETY,ALL,ALL,'사용자/서버·동의·삭제 격리','합성 DB·철회 경합','본인 기억·철회'),
    GateRule('receipts',Risk.SAFETY,ALL,ALL,'실행 금지·성공 영수증·예약 무결성','DB/Receipt·취소·재시작','실제 목록과 완료 안내 비교'),
    GateRule('delivery',Risk.SAFETY,DISCORD,DISCORD,'청자·원본 reply·최신성·중복','SDK mock·edit/delete·epoch 경합','허용 채널·본인 알림 대상'),
    GateRule('commands',Risk.SAFETY,DISCORD,DISCORD,'명령 권한·본인 ephemeral','SDK interaction mock','승인 후 실제 등록/표시'),
    GateRule('recovery',Risk.SAFETY,ALL,ALL,'단일 모델·실패/취소 복구','종료·재시작·소유 자원 해제','실패 후 오류/재시도'),
    GateRule('ui_portable',Risk.SAFETY,ALL,ALL,'UI와 실제 실행 상태 일치','격리 위젯·Portable CPU','첫 설치·복구·DPI'),
    GateRule('high_risk_claims',Risk.HIGH_RISK_FACTUALITY,ALL,ALL,'허위 완료·개인정보·권한 안내를 믿고 행동할 위험','실제 모델 발언과 DB/영수증 대조','잘못된 기능 안내 즉시 기록'),
    GateRule('audience',Risk.QUALITY,AUTO,AUTO,'자율 개입·후속/복귀 누락','원천 분리 다자 GPU 평가','사람 대화 오개입·봇 복귀'),
    GateRule('conversation',Risk.QUALITY,ALL,AUTO,'말투·재미·반복·장기 일관성','능동 대화·사람 평가','체감 품질·반복·관계 표현'),
    GateRule('long_running',Risk.SAFETY,ALL,AUTO,'장시간 누수·적체·자원 증가','장시간 실사용 로그','DEFERRED — USER REAL-WORLD TEST'),
    GateRule('live_discord',Risk.SAFETY,DISCORD,DISCORD,'실제 인증·등록·송신 검증','별도 승인 후 실서버 검증','정확한 승인 범위 확인',live_only=True),
)

READY_LABELS={ExecutionMode.LOCAL_CHAT:'LOCAL_CHAT_READY',
              ExecutionMode.DISCORD_DIRECT:'DISCORD_DIRECT_BETA_READY',
              ExecutionMode.DISCORD_AUTONOMOUS:'DISCORD_AUTONOMOUS_RELEASE'}


def assess_mode(mode,evidence,*,offline=True,live_authorized=False):
    """Typed development evidence, never model/config-authored authority.

    Applicable mandatory gates require PASS. N/A and DEFERRED cannot bypass
    them. Offline scope excludes only the separately reported live gate.
    """
    mode=ExecutionMode(mode)
    if set(evidence)-{r.key for r in RULES}:raise ValueError('Unknown release gate')
    rows=[];blockers=[];live_blockers=[]
    for rule in RULES:
        applies=mode in rule.modes
        status=GateStatus(evidence.get(rule.key,GateStatus.NOT_VERIFIED)) if applies else GateStatus.NOT_APPLICABLE
        required=applies and mode in rule.required
        if required and status!=GateStatus.PASS:
            live_blockers.append(rule.key)
            if not (offline and mode==ExecutionMode.DISCORD_DIRECT and rule.live_only):blockers.append(rule.key)
        rows.append(dict(key=rule.key,risk=rule.risk.value,status=status.value,required=required,
            live_only=rule.live_only,impact=rule.impact,verification=rule.verification,user_check=rule.user_check))
    ready=not blockers
    return dict(mode=mode.value,status='PASS' if ready else 'BLOCKED',ready=ready,
        readiness=READY_LABELS[mode] if ready else 'BLOCKED',
        scope='LOCAL ONLY' if mode==ExecutionMode.LOCAL_CHAT else 'OFFLINE READY' if ready and offline and mode==ExecutionMode.DISCORD_DIRECT else 'OFFLINE ONLY' if offline else 'LIVE VALIDATION',
        blockers=blockers,gates=rows,live_allowed=bool(mode in DISCORD and not offline and live_authorized and not live_blockers),
        local_testing_available=bool(mode==ExecutionMode.LOCAL_CHAT and all(g['status']=='PASS' for g in rows if g['required'] and g['risk']==Risk.SAFETY.value)),
        approval_required=mode in DISCORD and not live_authorized)


def current_mode_reports(technical):
    # Curated, bounded offline evidence. A social smoke probe is deliberately
    # not a certificate of generalization or high-risk factual accuracy.
    evidence={key:GateStatus.PASS for key in ('privacy','receipts','delivery','commands','recovery','ui_portable')}
    evidence.update(technical=GateStatus.PASS if technical else GateStatus.BLOCKED,
        high_risk_claims=GateStatus.FAIL,audience=GateStatus.FAIL,conversation=GateStatus.NOT_VERIFIED,
        long_running=GateStatus.DEFERRED,live_discord=GateStatus.BLOCKED)
    reports={mode.value:assess_mode(mode,evidence) for mode in ExecutionMode}
    for mode,report in reports.items():
        report['evidence_scope']='합성 회귀·SDK mock·로컬 GPU; 실서버/장시간 인증 아님'
    return reports
