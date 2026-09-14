# Keys inventory — NAMES ONLY, never values.
# Source: untracked local `.env` in this repo (gitignored, never committed).
# Values live in each agent's own profile `.env`. Status must be re-probed
# before use; see `shared/model-health.md`.

| Provider | Key names | Count | Status |
|---|---|---|---|
| Google AI Studio | GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, GOOGLE_API_KEY_3 | 3 | 429 on free tier (Sep 2026) |
| OpenRouter | OPENROUTER_API_KEY_1..5 | 5 | pooled for rotation |
| AgentRouter | AGENTROUTER_API_KEY | 1 | unknown |
| NVIDIA NIM | NVIDIA_API_KEY | 1 | worker limit 16/16 hit once (Sep 2026) |
| BAI | BAI_API_KEY | 1 | unknown |
| LLM7 | LLM7_KEY_1 | 1 | unknown |
| Groq | GROQ_KEY_1 | 1 | 401 invalid (Sep 2026) |
| Cerebras | CEREBRAS_KEY_1 | 1 | 402 out of credits (Sep 2026) |
| Mistral | MISTRAL_API_KEY | 1 | unknown |
| GitHub Models | GITHUB_MODELS_PAT | 1 | unknown |
