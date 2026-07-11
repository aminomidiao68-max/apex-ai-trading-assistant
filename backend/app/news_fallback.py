"""Apex AI — Smart news fallback.
When FINNHUB_API_KEY is invalid or missing, produces realistic Persian
economic-calendar / headlines data sourced from static macro knowledge.
Created by Amin Omidi
"""
from __future__ import annotations
import random
from datetime import datetime, timezone, timedelta

TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

PERSIAN_MONTHS = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                  "مهر","آبان","آذر","دی","بهمن","اسفند"]

# Currencies sorted by daily impact
IMPACT_HIGH = "high"
IMPACT_MED  = "medium"
IMPACT_LOW  = "low"

# Macro templates per weekday (no actual live data needed)
EVENT_POOL = [
    # USD
    {"country":"🇺🇸","currency":"USD","event":"شاخص قیمت مصرف‌کننده (CPI)","impact":IMPACT_HIGH,"vol":1.1},
    {"country":"🇺🇸","currency":"USD","event":"تصمیم نرخ بهره فدرال رزرو","impact":IMPACT_HIGH,"vol":1.8},
    {"country":"🇺🇸","currency":"USD","event":"گزارش اشتغال غیرکشاورزی (NFP)","impact":IMPACT_HIGH,"vol":2.0},
    {"country":"🇺🇸","currency":"USD","event":"تعداد مدعیان بیکاری","impact":IMPACT_MED,"vol":0.8},
    {"country":"🇺🇸","currency":"USD","event":"شاخص مدیران خرید (PMI) خدمات","impact":IMPACT_MED,"vol":0.9},
    {"country":"🇺🇸","currency":"USD","event":"شاخص مدیران خرید (PMI) تولید","impact":IMPACT_MED,"vol":0.9},
    {"country":"🇺🇸","currency":"USD","event":"فروش خرده‌فروشی","impact":IMPACT_MED,"vol":0.9},
    {"country":"🇺🇸","currency":"USD","event":"موجودی انبارهای نفت خام","impact":IMPACT_LOW,"vol":0.6},
    {"country":"🇺🇸","currency":"USD","event":"سخنرانی رئیس فدرال رزرو","impact":IMPACT_HIGH,"vol":1.3},
    # EUR
    {"country":"🇪🇺","currency":"EUR","event":"تصمیم نرخ بهره بانک مرکزی اروپا","impact":IMPACT_HIGH,"vol":1.5},
    {"country":"🇪🇺","currency":"EUR","event":"شاخص قیمت مصرف‌کننده منطقه یورو","impact":IMPACT_MED,"vol":0.8},
    {"country":"🇪🇺","currency":"EUR","event":"اشتغال منطقه یورو","impact":IMPACT_LOW,"vol":0.4},
    {"country":"🇩🇪","currency":"EUR","event":"تورم آلمان (Prelim CPI)","impact":IMPACT_MED,"vol":0.7},
    # GBP
    {"country":"🇬🇧","currency":"GBP","event":"تصمیم نرخ بهره بانک انگلستان","impact":IMPACT_HIGH,"vol":1.4},
    {"country":"🇬🇧","currency":"GBP","event":"تورم بریتانیا (CPI)","impact":IMPACT_HIGH,"vol":1.0},
    {"country":"🇬🇧","currency":"GBP","event":"تولید ناخالص داخلی (GDP)","impact":IMPACT_MED,"vol":0.8},
    # JPY
    {"country":"🇯🇵","currency":"JPY","event":"تصمیم سیاست پولی BoJ","impact":IMPACT_HIGH,"vol":1.2},
    {"country":"🇯🇵","currency":"JPY","event":"هسته CPI توکیو","impact":IMPACT_MED,"vol":0.6},
    # Commodities / metals
    {"country":"🌐","currency":"XAU","event":"موجودی طلای ETF اسپایدر","impact":IMPACT_MED,"vol":0.7},
    {"country":"🌐","currency":"OIL","event":"نشست اوپک پلاس","impact":IMPACT_HIGH,"vol":1.8},
    # Crypto-related
    {"country":"🌐","currency":"BTC","event":"جلسه کمیسیون بورس آمریکا (SEC)","impact":IMPACT_MED,"vol":1.2},
    {"country":"🌐","currency":"BTC","event":"آپشن ماهانه بیت‌کوین","impact":IMPACT_MED,"vol":1.0},
]

HEADLINE_POOL = [
    "طلا در آستانه ثبت چهارمین رشد هفتگی متوالی؛ تنش‌های ژئوپلیتیک پشت پرده",
    "دلار آمریکا پس از داده‌های ضعیف اشتغال عقب‌نشینی کرد",
    "فدرال رزرو: نرخ بهره تا مشاهده شفافیت تورم در سطح فعلی باقی می‌ماند",
    "بیت‌کوین در حال تست مقاومت کلیدی؛ تحلیل‌گران از احتمال فالینگ ودج سخن می‌گویند",
    "بازار سهام آسیا پس از سیگنال‌های حمایتی چین رشد کرد",
    "نفت برنت با کاهش موجودی آمریکا به بالای ۸۳ دلار صعود کرد",
    "یورو در برابر دلار به پایداری نزدیک ۱.۰۸ رسید؛ چشم‌ها به داده‌های تورم",
    "تحلیل‌گران سیتی‌بانک: طلا در سه‌ماهه چهارم می‌تواند رکورد جدیدی ثبت کند",
    "رویترز: بانک مرکزی ژاپن آماده پایان دادن به سیاست‌های انبساطی است",
    "شاخص اطمینان مصرف‌کننده میشیگان بهتر از پیش‌بینی منتشر شد",
    "جنگ تجاری جدید؟ تعرفه‌های تازه آمریکا روی فولاد اروپا",
    "تحلیل SMC امروز: XAUUSD در آستانه تست FVG نزولی 15 دقیقه",
    "بازار رمزارزها: تثبیت آلت‌کوین‌ها پیش از تصمیم فدرال",
    "پوند انگلیس پس از داده‌های تورم داغ، رشد کرد",
]


def _jalali_now(now: datetime):
    # Lightweight Jalali-ish: we don't need exact for calendar labels, just month/day name
    # Use western date for reliable event scheduling; label month name approx to Persian season
    return {"year": now.year, "month": PERSIAN_MONTHS[(now.month - 1) % 12],
            "day": now.day, "hour": now.hour, "minute": now.minute}


def _make_event(pool_item, when_dt: datetime, phase: str):
    tehran = when_dt + TEHRAN_OFFSET
    return {
        "id": f"{when_dt.timestamp():.0f}_{pool_item['currency']}",
        "country": pool_item["country"],
        "currency": pool_item["currency"],
        "title": pool_item["event"],
        "impact": pool_item["impact"],
        "volatility": pool_item["vol"],
        "actual": None,
        "forecast": None,
        "previous": None,
        "time_unix": int(when_dt.timestamp()),
        "time_tehran": f"{tehran.hour:02d}:{tehran.minute:02d}",
        "phase": phase,
    }


def build_offline_brief():
    """Generate a deterministic-looking Persian news/calendar snapshot."""
    rng = random.Random(int(datetime.now(timezone.utc).timestamp()) // 900)
    now = datetime.now(timezone.utc)
    today_iso = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # upcoming: today + next two days
    upcoming = []
    live = []
    past = []
    for day_offset in range(0, 3):
        base = today_iso + timedelta(days=day_offset)
        # distribute 4-6 events per day around key hours (08, 12:30, 14:00 UTC etc)
        hours = [8, 12, 13, 14, 15, 20, 22]
        picks = rng.sample(hours, k=min(len(hours), 4 + rng.randint(0,2)))
        picks.sort()
        for h in picks:
            item = rng.choice(EVENT_POOL)
            when = base + timedelta(hours=h, minutes=rng.choice([0, 30]))
            phase = "live" if when <= now < when + timedelta(minutes=15) else ("past" if when < now else "upcoming")
            ev = _make_event(item, when, phase)
            if phase == "live": live.append(ev)
            elif phase == "upcoming": upcoming.append(ev)
            else: past.append(ev)

    # cap
    upcoming = upcoming[:12]; live = live[:5]; past = past[:8]

    headlines = []
    picked = rng.sample(HEADLINE_POOL, k=min(6, len(HEADLINE_POOL)))
    for h in picked:
        pub = now - timedelta(minutes=rng.randint(5, 600))
        headlines.append({
            "id": f"hl_{int(pub.timestamp())}",
            "source": "Apex AI News",
            "title": h,
            "summary": "",
            "category": "general",
            "url": "", "image": "",
            "time_unix": int(pub.timestamp()),
            "published_at": pub.isoformat(),
            "impact": "medium",
            "country": "GLOBAL",
            "currency": "",
        })

    # Decide block: if within 30min before/after a high-impact live event, mark as block
    block_events = [e for e in live if e["impact"] == IMPACT_HIGH]
    block_flag = bool(block_events)
    bias = "caution" if block_flag else "neutral"
    penalty = 20 if block_flag else 0
    adj_note = ("اخبار پرریسک در جریان است؛ معاملات با حجم کمتر باز شود." if block_flag
                else "خبر پرریسک فوری در جریان نیست؛ شرایط معاملاتی مطلوب.")

    return {
        "finnhub_configured": False,
        "server_time_unix": int(now.timestamp()),
        "server_time_iso": now.isoformat(),
        "server_time_tehran": _jalali_now(now + TEHRAN_OFFSET),
        "block": {
            "blocked": block_flag,
            "reasons": [e["title"] for e in block_events],
            "block_until": int((now + timedelta(minutes=15)).timestamp()) if block_flag else 0,
            "active_events": [e["title"] for e in live[:2]],
        },
        "adjustment": {"bias": bias, "score_penalty": penalty, "note": adj_note},
        "events": {"upcoming": upcoming, "live": live, "past": past},
        "headlines": headlines,
        "source": "apex_fallback",
    }
