#!/usr/bin/env python3
"""
build_model_index.py

Parses README.md of the (forked) awesome-freellm-apis repo and produces
models.json: a structured, machine-readable index of free LLM models,
meant to be read by an orchestrator agent that assigns tasks to
sub-agents based on task weight/type.

It combines three tables from the README:
  1. "Permanent Free Tiers"      -> credit_card_required, provider max context
  2. "Renewable Credits"         -> same, for credit-based providers
  3. "Quick Reference"           -> base_url, api_key_url
  4. "Best Free Models by Provider" -> the actual per-model rows
     (this is the primary source of the model-level entries)

Output schema (models.json):
{
  "generated_at": "...",
  "source_commit_note": "parsed from local README.md at build time",
  "model_count": N,
  "models": [
    {
      "provider": "Groq",
      "model_name": "Moonshot Kimi K2",
      "model_id": "moonshotai/kimi-k2-instruct",
      "max_context": 131072,
      "max_context_display": "131K",
      "rate_limit": "See provider",
      "credit_card_required": "No",
      "base_url": "https://api.groq.com/openai/v1",
      "api_key_url": "https://console.groq.com/keys",
      "weight_tier": "medium"       # light | medium | heavy
    },
    ...
  ]
}

weight_tier heuristic (tune as needed for your orchestrator):
  - heavy  : max_context >= 500,000
  - medium : 128,000 <= max_context < 500,000
  - light  : max_context < 128,000  (or unknown/0)
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

README_PATH = Path("README.md")
OUTPUT_PATH = Path("models.json")
ENV_EXAMPLE_PATH = Path(".env.example")


def parse_context(text: str) -> int:
    """'1M' -> 1_000_000, '262K' -> 262_000, '131K' -> 131_000, '0' -> 0."""
    text = text.strip()
    m = re.match(r"([\d.]+)\s*([MK]?)$", text, re.IGNORECASE)
    if not m:
        return 0
    num, suffix = m.groups()
    num = float(num)
    if suffix.upper() == "M":
        return int(num * 1_000_000)
    if suffix.upper() == "K":
        return int(num * 1_000)
    return int(num)


def weight_tier(max_context: int) -> str:
    if max_context >= 500_000:
        return "heavy"
    if max_context >= 128_000:
        return "medium"
    return "light"


def clean_cell(cell: str) -> str:
    # strip markdown link syntax [text](url) -> text
    cell = cell.strip()
    cell = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cell)
    # strip raw HTML anchor tags <a href="...">text</a> -> text
    cell = re.sub(r'<a\s+[^>]*>(.*?)</a>', r"\1", cell, flags=re.IGNORECASE)
    # strip any other stray HTML tags
    cell = re.sub(r"<[^>]+>", "", cell)
    cell = cell.strip("`").strip()
    return cell


def extract_link_url(cell: str) -> str | None:
    # markdown style: [text](https://...)
    m = re.search(r"\((https?://[^)]+)\)", cell)
    if m:
        return m.group(1)
    # HTML style: <a href="https://...">
    m = re.search(r'href="(https?://[^"]+)"', cell)
    return m.group(1) if m else None


def extract_code(cell: str) -> str | None:
    m = re.search(r"`([^`]+)`", cell)
    return m.group(1) if m else None


def find_table(md_text: str, heading_pattern: str) -> list[list[str]]:
    """
    Find a markdown table that appears after a heading matching
    heading_pattern, and return its rows as lists of raw cell strings
    (still containing markdown link syntax).
    """
    heading_re = re.compile(heading_pattern, re.IGNORECASE)
    lines = md_text.splitlines()

    start_idx = None
    for i, line in enumerate(lines):
        if heading_re.search(line):
            start_idx = i
            break
    if start_idx is None:
        return []

    # scan forward for the first table (a line starting with '|')
    table_lines = []
    in_table = False
    for line in lines[start_idx:]:
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            table_lines.append(stripped)
        elif in_table and not stripped.startswith("|"):
            break

    if not table_lines:
        return []

    rows = []
    for line in table_lines:
        # skip the header-separator row, e.g. |---|---|
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def build_quick_reference_map(md_text: str) -> dict:
    rows = find_table(md_text, r"Quick Reference.*Base URLs")
    if not rows:
        return {}
    header, *body = rows
    ref = {}
    for r in body:
        if len(r) < 4:
            continue
        provider = clean_cell(r[0])
        base_url = clean_cell(r[1]).strip("`")
        api_key_url = extract_link_url(r[2]) or ""
        credit_card = clean_cell(r[3])
        ref[provider] = {
            "base_url": base_url,
            "api_key_url": api_key_url,
            "credit_card_required": credit_card,
        }
    return ref


def build_tier_map(md_text: str) -> dict:
    """Merge 'Permanent Free Tiers' + 'Renewable Credits' tables -> per-provider max context."""
    tier_map = {}
    for pattern in [r"Permanent Free Tiers", r"Renewable Credits"]:
        rows = find_table(md_text, pattern)
        if not rows:
            continue
        header, *body = rows
        for r in body:
            if len(r) < 4:
                continue
            provider = clean_cell(r[0])
            max_ctx_raw = clean_cell(r[3])
            tier_map[provider] = parse_context(max_ctx_raw)
    return tier_map


def build_models(md_text: str, quick_ref: dict, tier_map: dict) -> list[dict]:
    rows = find_table(md_text, r"Best Free Models by Provider")
    if not rows:
        print("[warn] could not find 'Best Free Models by Provider' table", file=sys.stderr)
        return []

    header, *body = rows
    models = []
    current_provider = ""
    for r in body:
        if len(r) < 5:
            continue
        provider_cell = clean_cell(r[0])
        if provider_cell:
            current_provider = provider_cell
        provider = current_provider

        model_name = clean_cell(r[1])
        model_id = extract_code(r[2]) or clean_cell(r[2])
        max_ctx_raw = clean_cell(r[3])
        rate_limit = clean_cell(r[4])

        max_context = parse_context(max_ctx_raw)
        # fall back to the provider-level max context if per-model is 0/unknown
        if max_context == 0:
            max_context = tier_map.get(provider, 0)

        ref = quick_ref.get(provider, {})

        models.append({
            "provider": provider,
            "model_name": model_name,
            "model_id": model_id,
            "max_context": max_context,
            "max_context_display": max_ctx_raw,
            "rate_limit": rate_limit,
            "credit_card_required": ref.get("credit_card_required", ""),
            "base_url": ref.get("base_url", ""),
            "api_key_url": ref.get("api_key_url", ""),
            "weight_tier": weight_tier(max_context),
        })

    return models


def env_var_name(provider: str) -> str:
    """'Z AI (Zhipu AI)' -> 'Z_AI_ZHIPU_AI'"""
    name = re.sub(r"[^A-Za-z0-9]+", "_", provider).strip("_").upper()
    return name


def write_env_example(models: list[dict]) -> None:
    """
    One BASE_URL / API_KEY pair per unique provider (first model with a
    base_url wins). Regenerated every run so newly discovered providers
    automatically get an entry, and providers that disappear from the
    upstream README are automatically dropped.
    """
    seen: dict[str, dict] = {}
    for m in models:
        if m["provider"] not in seen and m.get("base_url"):
            seen[m["provider"]] = m

    lines = [
        "# .env.example",
        "# این فایل به‌صورت خودکار توسط build_model_index.py از روی models.json ساخته می‌شود — دستی ویرایشش نکنید.",
        "# کپی کن به .env و مقدار *_API_KEY هر provider که استفاده می‌کنی رو پر کن؛ BASE_URL نیازی به تغییر ندارد.",
        "",
    ]
    for provider, m in sorted(seen.items()):
        name = env_var_name(provider)
        key_url = m.get("api_key_url") or "—"
        lines.append(f"# {provider} — دریافت کلید: {key_url}")
        lines.append(f"{name}_BASE_URL={m['base_url']}")
        lines.append(f"{name}_API_KEY=")
        lines.append("")

    ENV_EXAMPLE_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[info] wrote {len(seen)} provider entries to {ENV_EXAMPLE_PATH}")


def main():
    if not README_PATH.exists():
        print(f"[error] {README_PATH} not found — run this from the repo root after checkout.", file=sys.stderr)
        sys.exit(1)

    md_text = README_PATH.read_text(encoding="utf-8")

    quick_ref = build_quick_reference_map(md_text)
    tier_map = build_tier_map(md_text)
    models = build_models(md_text, quick_ref, tier_map)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit_note": "parsed from local README.md at build time",
        "model_count": len(models),
        "models": models,
    }

    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[info] wrote {len(models)} models to {OUTPUT_PATH}")

    write_env_example(models)


if __name__ == "__main__":
    main()
