# Routing guide — which provider type for which task.
# Generic for all agents. Personal picks stay in each agent's own profile config.

| Task | Provider | Why |
|---|---|---|
| Coding / repo work | nvidia | strong coder, no daily cap, stable |
| Long-text / image / audio summarize | google-ai-studio | 1M context, multimodal |
| General fallback (others 429) | opencode | rotating free pool |
| Fast small inference | groq | lowest latency |
| One-key multi-model | openrouter | single endpoint |

Rules:
- On 429: wait 60–90s, retry once, then switch provider (don't hammer).
- Never commit keys. `key_env` names only; values live in the agent's `.env`.
- Before delegating, read `shared/providers.yaml` and set model/provider explicitly.
