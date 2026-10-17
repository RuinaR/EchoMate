# 로컬 Ollama 대화 기준선

## 상태
- 로컬 Ollama `/api/chat` 연동, 현 대화 문맥 빌더, 출력 텍스트 필터, CLI 생성 시험을 구현.
- 아직 **실제 Ollama 모델 호출은 사용자의 Windows PC에서 검증 전**.
- AI 학습, Discord 실시간 연결, 페르소나 아티팩트 및 자동 참여 결정기는 미구현.
- 스타일 프로필은 명시적 짧은 스타일 문자열만 사용. 사용자의 Discord 원본 메시지를 모델에 훈련/전송하지 않는다.

## 요구 환경
- Python 3.11+ (표준 라이브러리)
- 본인 PC에서 Ollama 실행, 예: `ollama list`에 `qwen3.5:9b-q4_K_M` 존재
- Discord 계정·토큰 필요 없음.

## 실행
```powershell
git pull origin main
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
ollama list
python -m echomate_studio.chat_probe --model "qwen3.5:9b-q4_K_M" --message "오늘 메이플 할래?"
```

`ollama list`에서 출력되는 실제 모델 이름을 사용한다.

## 안전 경계 / 검증
- 통신 대상은 127.0.0.1/localhost Ollama로 제한하며 원문 데이터 학습 없음.
- 봇이라는 사실을 시스템 메시지에 표시.
- Discord 서버 커스텀 이모지, URL 및 이미지 마크다운 출력 필터. Unicode 이모지 허용.
- 현재 CLI는 단발 테스트. Discord로 메시지를 보내지 않음.
- 다음: 복수 턴 평가 세트/성능 계측, 페르소나 아티팩트(버전/품질 검증), Bot 연결.
