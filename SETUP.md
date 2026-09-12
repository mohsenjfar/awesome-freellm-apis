# Fork Sync + Model Index (for agent orchestration)

این نسخه برای زمانی است که یک **ایجنت اصلی (orchestrator)** دارید که پیش از
تخصیص کار به ساب‌ایجنت‌ها، باید لیست مدل‌های رایگان موجود و "سنگینی" هرکدام
را ببیند. به‌جای جستجوی خام وب، این روش مستقیماً از مخزن پرستاره و
به‌روز `open-free-llm-api/awesome-freellm-apis` استفاده می‌کند.

## فایل‌ها

- **`.github/workflows/sync-and-index.yml`** — هر روز ساعت ۰۶:۰۰ UTC:
  1. فورک شما را با upstream sync می‌کند (fast-forward).
  2. `build_model_index.py` را اجرا می‌کند تا `models.json` بازسازی شود.
  3. اگر تغییری بود، commit + push خودکار.
- **`build_model_index.py`** — جدول‌های `README.md` را پارس می‌کند و یک
  ایندکس ساختاریافته JSON می‌سازد.
- **`models.json`** — خروجی نمونه (بعد از اولین اجرای واقعی workflow،
  این فایل خودش را با داده‌ی تازه بازنویسی می‌کند).
- **`.env.example`** — به‌ازای هر provider یکتا (۳۰ مورد فعلاً) یک جفت
  `PROVIDER_BASE_URL` / `PROVIDER_API_KEY=` می‌سازد. این فایل هم خودکار
  از روی `models.json` بازسازی می‌شود، پس اگر provider جدیدی upstream اضافه
  شود، خودش ظاهر می‌شود؛ اگر provider‌ای حذف شود، خودش هم حذف می‌شود.
  کپی‌اش کنید به `.env` و فقط مقدار `*_API_KEY` هایی که لازم دارید را پر کنید.

## راه‌اندازی

1. مخزن `open-free-llm-api/awesome-freellm-apis` را در گیت‌هاب **Fork** کنید.
2. دو فایل `.github/workflows/sync-and-index.yml` و `build_model_index.py`
   را داخل فورک خودتان (در ریشه‌ی ریپو) اضافه و commit کنید.
   *(نیازی به `SERPER_API_KEY` یا هیچ secret دیگری نیست — این نسخه فقط از
   داده‌ی خود ریپو استفاده می‌کند.)*
3. مطمئن شوید در `Settings → Actions → General → Workflow permissions`
   گزینه‌ی **"Read and write permissions"** فعال باشد (برای اینکه workflow
   بتواند commit/push کند).
4. برای تست فوری: تب **Actions → Daily fork sync + model index rebuild →
   Run workflow**.

## چطور ایجنت اصلی از `models.json` استفاده کند

هر ورودی در آرایه‌ی `models` این شکلی است:

```json
{
  "provider": "Groq",
  "model_name": "Moonshot Kimi K2",
  "model_id": "moonshotai/kimi-k2-instruct",
  "max_context": 131000,
  "max_context_display": "131K",
  "rate_limit": "See provider",
  "credit_card_required": "No",
  "base_url": "https://api.groq.com/openai/v1",
  "api_key_url": "https://console.groq.com/keys",
  "weight_tier": "medium"
}
```

`weight_tier` سه مقدار دارد:
- **`heavy`** — max_context ≥ 500K (برای کارهای پیچیده/context بلند)
- **`medium`** — 128K ≤ max_context < 500K (کارهای معمولی)
- **`light`** — max_context < 128K (کارهای ساده/سریع)

ایجنت اصلی می‌تواند مثلاً:
```python
import json
data = json.load(open("models.json"))

def pick_model(task_weight: str, avoid_credit_card=True):
    candidates = [
        m for m in data["models"]
        if m["weight_tier"] == task_weight
        and (not avoid_credit_card or m["credit_card_required"] == "No")
    ]
    return candidates[0] if candidates else None
```

## نکات

- این ایندکس فقط "بهترین مدل هر provider" را شامل می‌شود (همان جدول
  `Best Free Models by Provider` در README بالادستی)، نه همه‌ی ۴۵۰+ مدل —
  چون دیتاست کامل فقط روی freellm.net در دسترس است، نه در خود ریپو.
- اگر ساختار جدول‌های README بالادستی تغییر کند (مثلاً عنوان بخش‌ها عوض
  شود)، پارسر ممکن است نتیجه‌ی خالی بدهد — در این صورت لاگ workflow را چک
  کنید (پیام `[warn] could not find ...` نشانه‌ی این مورد است).
- `weight_tier` صرفاً بر اساس max context است؛ اگر معیار دیگری (مثل سرعت،
  قابلیت reasoning، یا هزینه) هم مهم است، به‌راحتی می‌توانید تابع
  `weight_tier()` در `build_model_index.py` را گسترش دهید.
