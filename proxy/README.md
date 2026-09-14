# Failover proxy — one endpoint, many keys

Agents point at a single URL and pick a logical model. Key rotation on
429 is automatic and invisible to the caller.

## Start

```bash
cd proxy
cp .env.example .env   # fill in real keys (never commit .env)
docker compose up -d    # single worker only
```

Verify:

```bash
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

## Logical models

| Name | Backed by | Use for |
|---|---|---|
| `agent-coding` | 5× OpenRouter keys | repo work, coding agents |
| `agent-fast` | Groq + Cerebras keys | quick tasks |
| `agent-reader` | 3× Google keys | long-text / multimodal summarize |

Point any OpenAI-compatible client at `http://<host>:4000/v1`
with `model: "<logical-name>"`.

## Add a key

1. Append one `model_list` deployment in `litellm_config.yaml`
   with the same `model_name` and `api_key: os.environ/NEW_KEY`.
2. Add `NEW_KEY=` to `.env.example` (empty) and your real `.env`.
3. `docker compose restart`.

## Failover behavior

`allowed_fails: 1` — first 429 rotates immediately.
`cooldown_time: 60` — a 429'd key rests 60s while traffic continues.
The client only sees the final answer.
