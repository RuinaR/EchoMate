# EchoMate persona/latency research review — 2026-10-18
## Observation on actual QA
- Windows 58 unit tests passed, but Qwen style-profile reply falsely said MapleStory is no longer available, and gave a long formal answer. Unit success != quality success.
- Uploaded aggregate profile: 304997 messages, 270989 filtered text, weighted mean 7.25 characters; ㅋㅋ 0.0402, ㅠ/ㅜ 0.0051, question 0.1194, emoji 0.0039.
- Aggregate stats are far from sufficient for accurate speech imitation, and strong prompt rules can still be ignored. Need blind human A/B tests with multiple prompts.
## Literature and open projects
- Lost in the Middle (Liu et al., TACL 2024): https://aclanthology.org/2024.tacl-1.9/ — increasing prompt context length does not necessarily improve accuracy; retrieve relevant recent turns, keep salient facts close to the question. Adoption: keep RAM buffer independent from prompt budget, plan relevance reranking.
- mimic-bot persona research: https://github.com/v4rgas/mimic-bot/blob/main/docs/persona-research.md — style caricature and overuse of catchphrases; adoption: mundane baseline and approximate observed frequency, avoid catchphrase parroting. Treat project claims as engineering hypotheses, not proven paper results.
- PersonaAgent: https://github.com/yolo0731/PersonaAgent — separate authorized style sources and factual knowledge sources. Adoption: distinguish style/context/current facts, don't use style stats as fact evidence.
- llmcord: https://github.com/bytesPerso/discord-llm-chatbot — provider abstraction and configurable local model settings. Adoption later: configurable per-operation generation settings and latency monitoring.
## Immediate fixes shipped
- Conversation system instruction now prioritizes ordinary invitation interpretation and avoids inventing service-state claims; short casual Korean default.
- Derived profile instruction emphasizes brief everyday replies and low emoji rate; baseline rather than caricature.
- Probe --timing prints total wall-clock generation seconds (not token timing) to identify slow calls before optimizing Ollama settings.
## Evaluation next
- Local A/B prompts: '오늘 메이플 할래?', '오늘 보스 몇 시에 갈까?', '아이고 힘들다', '그거 어떻게 해?', 'ㅋㅋㅋㅋ'. Check facts, length, naturalness, unnecessary emojis, response latency.
- Research baseline improvements should be tested against the old version; no claim of quality improvement before user tests.
- Persona model fine tuning or stylistic retrieval using Discord data remains gated by data-use conditions; current profile only stores aggregates.