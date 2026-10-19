# 배포 의존성 안내

Portable 후보는 기존 검증 환경의 Python 및 공개 Python 패키지를 번들한다. 각 패키지의 dist-info/license 파일과 Python LICENSE를 런타임 폴더에 보존한다. torch의 CUDA DLL 등은 원래 패키지에 포함된 제3자 구성 요소이며 별도 GPU 드라이버를 대체하지 않는다. 라이선스 파일을 제거한 경량 패키지를 배포하지 않는다.

EchoMate 소스는 소유자의 명시 선택으로 MIT를 적용했다. [프로젝트 LICENSE](../LICENSE)와 제3자 라이선스 준수는 별개다. 전체 의존성 license/NOTICE 검토와 서명된 일반 배포 승인은 아직 완료되지 않았다. 공개 Release 자산으로 업로드하지 않고 로컬 검증 후보만 생성했다. 모델 가중치/개인 adapter/토큰/사용자 DB는 포함하지 않는다.

구현은 [Python](https://docs.python.org/3/license.html), [PyTorch](https://github.com/pytorch/pytorch/blob/main/LICENSE), [Transformers](https://github.com/huggingface/transformers/blob/main/LICENSE), [discord.py](https://github.com/Rapptz/discord.py/blob/master/LICENSE)의 라이선스를 함께 확인해야 한다. 모델은 별도 [공식 카드](https://huggingface.co/google/gemma-4-12B-it)의 라이선스를 따른다.
