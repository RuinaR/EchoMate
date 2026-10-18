# 데이터·프라이버시 및 학습 사용 정책

## 데이터 입력 원칙
- 1개 이상의 독립 채널 JSON 파일을 입력할 수 있다. 각 파일은 별개 채널로 취급하고 출처·소유권·이용 조건을 독립적으로 확인한다.
- 첫 검증 자료는 사용자가 직접 신청·제공한 **본인 Discord 데이터 패키지**에서 나온 파일이다. 추가 자료는 적절한 권리·허가 조건을 확인한 뒤 처리한다.
- 본인의 다른 서버/DM/결제/로그인/IP 데이터는 프로젝트 입력에 불필요하다.
- 로컬 검사기에서는 `messages`·`servers` 구조를 필요한 범위에서 식별하되, 원본 ZIP 업로드나 원격 API 전달을 기본값으로 만들지 않는다.
- 사용자가 고른 서버의 *본인 메시지*만 별도 복사·가공하고, 원본 패키지는 임의 삭제하지 않는다.
- 데이터 처리 전 출처, 사용 목적, 동의, Discord 정책 및 라이선스를 점검한다.
- Discord API로 얻은 콘텐츠의 AI 학습은 Discord의 명시적 허가가 필요할 수 있다. 개인 데이터 패키지의 AI 학습 허용 여부도 별도 검토 전 '허가됨'으로 표시하지 않는다.

## 저장/삭제
- 원본 ZIP, 변환 텍스트, SQLite, 인덱스, LoRA, eval 샘플 및 개인 정보는 .gitignore 대상.
- 설정 UI에서 데이터 출처·포함 범위·분석 여부·학습 허가 상태 확인.
- 삭제 요청 시 원본 사용자 데이터/파생 인덱스/학습 어댑터를 식별하여 삭제·재구축.
- 암호화된 로컬 보관 권장. 백업 역시 개인 파일로 취급.
- 진단 로그에 메시지 원문/토큰/첨부 URL 저장 금지.

## 기록 신뢰성
- 원본 메시지, 자동 분류, 추정 문맥, 합성 예문을 서로 다른 타입으로 보관.
- 다른 사람의 실제 채팅이나 감정을 '복원했다'고 단정하지 않음.
- 친구별 확장 시 각 제공자 동의와 Discord 정책을 따로 확인.

## 공식 참고
- https://support.discord.com/hc/en-us/articles/360004957991-Your-Discord-Data-Package
- https://support.discord.com/hc/en-us/articles/360004027692-Requesting-a-Copy-of-your-Data
- https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy

## 2026-10-18 — Training rights and corpus gate clarification
- Discord Developer Policy section 21 explicitly disallows AI/ML training on message content obtained through Discord APIs without Discord's express permission: https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy
- Official Discord personal Data Package contains the account holder's own messages and timestamps, per https://support.discord.com/hc/en-us/articles/360004957991-Your-Discord-Data-Package . That separate acquisition route does NOT automatically establish authorization to train an AI model; verify current conditions before enabling actual corpus export or fine-tuning.
- Current owner permission covers offline aggregate diagnostics, not publication of original/private messages. Never put raw messages, redacted snippets, identifiers, tokenized samples or training examples in public GitHub. Independently assess privacy exposure of other people, including contextual details in own messages.
- Single-speaker corpus is not an interlocutor Q&A dataset. Do not synthesize false dialogue labels from adjacent self-messages. Prefer controlled style/completion objectives only after source clearance and human review.
- `persona_split_audit.py` produces only aggregate candidate counts, using per-file chronological last ~10% validation and ephemeral text hashes for cross-split overlap checks. This is a diagnostic, NOT a training sample writer, approval or proof of privacy clearance. Exact split and duplicates must be checked again on any eventual approved dataset.

## 2026-10-18 — Clarification: owner export and content retention
- Owner preference: do NOT filter out health-related, sexual, or aggressive/profane utterances merely due to their topic or tone. Preserve authentic writing style; distinguish content labeling from exclusion and govern deployment separately. Protect credentials, identifiers, and private third-party information.
- Discord Developer Policy section 21 refers specifically to **message content obtained through APIs**. The current user supplied an **official owner-requested personal Data Package**, which is a distinct acquisition method. Section 21 alone does not establish a prohibition for this export. Neither does the Data Package help article explicitly grant permission for AI training. Record this distinction rather than treating API-specific rules as a blanket ban or representing personal-export training as definitively authorized. Other terms, privacy and third-party rights may matter.

## 2026-10-18 — Audit is not authorization
- Private corpus build now rejects overwriting an existing nonempty output directory; manually select a new directory for a new reviewed dataset version.
- Bounded heuristic cross-split near-duplicate checks use textual anchors and may miss paraphrases or contextual identity leaks. A zero-flag report alone is not sufficient training consent, legal permission or comprehensive privacy review.
- Never upload training JSONL, owner exports, LoRA derived from private messages, private eval prompts or raw identifiers to the public repository.
