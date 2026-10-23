# EchoMate

내 Windows PC의 로컬 AI로 운영하는 Discord 동반자입니다. 각 사용자는 **자신의 Discord 봇 계정과 토큰**을 사용합니다. 한국어 중심이며 허용한 서버·채널·스레드에서만 동작합니다.

EchoMate 소스는 [MIT](LICENSE) 라이선스입니다. 모델·번들 의존성은 [각 라이선스](docs/THIRD-PARTY-NOTICES.md)를 따릅니다.

2026-10-23 재개에서는 버튼을 누른 뒤 같은 버튼 안에서 놓을 때 실행하도록 개선하고, 초기 설정·모델 빈 상태·고배율 화면 겹침을 정리했습니다. 기존 분할 모델의 로딩 피크 약13GiB를 재현했으며 추가 절감을 입증하지 못해 안전 기준을 유지합니다. 원본 기본 모델과 분할 복사본은 서로 다른 선택입니다. 실제 서버의 `/동의` 비표시와 사회적 대화 품질 차단은 남아 있습니다. [최신 메모리·UI 검증](docs/RESUMED-MEMORY-UX-QA.md).

분할 메시지는 실제 원본을 따로 보존한 발언 뷰로 처리합니다. 교차 화자·생성 중 보충·수정/삭제·원본 답장을 검증했으며, 애매한 의미 경계와 사회적 판단의 릴리즈 차단은 남아 있습니다. [분할 발언 계약과 검증](docs/MULTI-MESSAGE-UTTERANCES.md).

표현 고급 설정은 슬라이더와 선택 버튼으로 조절하며, 적용 전에는 저장되지 않습니다. 버튼·목록의 누름·선택·포커스 상태도 구분합니다. [입력과 인터랙션 QA](docs/UI-INTERACTION-GUIDE.md).

최신 [사회적 판단 정밀 QA](docs/PRECISION-SOCIAL-QA.md)와 [UI 동작 QA](docs/UI-ACTION-QA.md)에서도 정식 릴리즈는 **BLOCKED**입니다. 운영 자료를 건드리지 않고 창과 설정을 직접 확인하려면 `EchoMate-Check.vbs`를 사용하세요. 가상 정보와 별도 저장소로 실행하며 실제 Discord 연결을 차단합니다. [10~15분 사용자 확인](docs/USER-MANUAL-QA.md)은 아직 사용자가 완료한 결과가 아닙니다.

**현재는 검증 후보입니다.** 기본 모델의 실제 GPU 로딩·모델 전환·Portable 로컬 미리보기는 확인했습니다. 사회적 청자 평가에 오개입·후속 대화 누락이 남아 있으며, 20분 모의 운용을 완료했지만 깨끗한 다른 Windows 설치와 장시간 실사용은 미검증입니다. 일반 배포 릴리즈 PASS가 아닙니다. [배포 QA](docs/DISTRIBUTION-QA.md)를 확인하세요.

최신 안정화에서는 완료된 대화 기록이 32개에 이르면 새 직접 질문이 차단되는 문제를 수정했습니다. 원본 가중치를 보존한 공식 shard 복사본에서 로딩 commit 피크 31.35→13.01GiB도 확인했습니다. 사회적 청자 품질 차단은 남아 있습니다. 실행 결과와 검증 범위는 [최종 안정화 QA](docs/STABILIZATION-QA.md)를 따르세요.

## 처음 사용하기

1. Portable 폴더 전체를 쓰기 가능한 위치에 풀고 `EchoMate.vbs`를 실행합니다. 후보 패키지에 Python 런타임을 포함하며 별도 Git·PowerShell 명령을 요구하지 않습니다.
2. **처음 사용 안내**에서 공식 Discord 봇 생성·Message Content Intent·최소 권한 안내를 따릅니다. 본인 Discord 사용자 ID와 Bot Token을 마스킹된 입력란에 등록합니다.
3. **AI 모델**에서 Gemma 4 12B 폴더를 선택하거나 `models/` 아래에 넣고 다시 검색합니다. 기존 Hugging Face 캐시도 검색합니다. 가중치는 배포판에 포함하지 않습니다.
4. **성격과 기분**에서 캐릭터를 편집·저장합니다. 모델과 캐릭터는 별개입니다. 로컬 미리보기는 Discord에 전송하거나 기억·친밀도를 갱신하지 않습니다.
5. **대화할 곳**에서 직접 새로고침하고 허용 서버·채널·스레드와 응답 방식을 저장한 뒤 **봇 켜기**를 누릅니다. 허용하지 않은 곳에서는 동작하지 않습니다.

이번 차수에서 실계정 로그인·Gateway·명령 동기화·서버 메시지 송신은 수행하지 않았습니다. 초기 UI 검사에서 합성 가짜 토큰 인증 요청2건이 나간 경계 오류는 폐기·보강하고 [정정 기록](docs/PRECISION-SOCIAL-QA.md)에 남겼습니다. [설치와 데이터 위치](docs/USER-INSTALLATION.md) · [모델 관리](docs/MODEL-REGISTRY.md) · [캐릭터](docs/CHARACTER-PROFILES.md).

## 모델과 데이터

- 공식 기본 모델은 **Gemma 4 12B** 하나입니다. 개인 말투/adult 고정 모델 버튼을 제거했습니다. 개인 LoRA·실험 자료는 삭제하지 않습니다.
- 1차 로더는 Gemma 4 Unified Transformers/Safetensors + 실행 시 NF4입니다. GGUF·LoRA도 발견하지만 현재 앱에서 적용할 수 없으며 이유를 표시합니다. 파일 검사와 실제 추론 검증을 구분합니다.
- 성인 유머는 기본 OFF인 캐릭터 정책입니다. 기존 연령 제한·동의/불편 표현·권한 경계를 유지합니다.
- Discord에는 본인의 친밀도·장기 기억·대화 요약을 각각 관리하는 **`/동의` 하나**를 제공합니다. 나머지 관리는 Windows 앱에서 합니다.
- 새 설치의 토큰은 현재 Windows 계정의 DPAPI로 암호화합니다. 기존 자료는 덮어쓰거나 자동 삭제하지 않습니다. 모델·토큰·DB·개인 로그는 GitHub에 포함하지 않습니다.
- 출력은 텍스트와 Unicode 반응입니다. 스티커·등록 미디어 송신을 복구하지 않았습니다.

## 요구 환경과 검증 범위

검증한 GPU 환경은 RTX4070Ti SUPER16GB / RAM32GB입니다. 모든 NVIDIA GPU·CPU 전용·다른 Windows 버전의 지원을 뜻하지 않습니다. Windows 메모리 할당 여유도 필요하며 부족하면 앱이 숫자와 함께 안내합니다. 이전1455 중단 후 실제 로딩을 재개하고 해제 시 큰 VRAM 예약이 남는 문제도 수정했습니다. [실제 검사와 미검증](docs/DISTRIBUTION-QA.md) · [전체 지연 계측](docs/PERFORMANCE-PIPELINE.md).

개발자는 [AI-HANDOFF](docs/AI-HANDOFF.md)부터 읽으세요. 소스 실행은 기존 가상환경의 `EchoMate.vbs`/`EchoMate.cmd`를 유지합니다. Portable 빌드 도구는 `tools/build_portable.py`이며 일반 사용자용 명령이 아닙니다. 과거 개발·실험 기록은 [README 이력](docs/README-HISTORY.md)에 보존했습니다.
