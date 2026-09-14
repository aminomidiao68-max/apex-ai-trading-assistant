import os
import logging

logger = logging.getLogger("apex.strategy_helper")

class StrategyGroundedHelper:
    _master_doc_cache = None

    @classmethod
    def get_master_document_content(cls) -> str:
        if cls._master_doc_cache is not None:
            return cls._master_doc_cache
        
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "MASTER-FULL-Integrated-v3.md"),
            os.path.join(os.path.dirname(__file__), "..", "..", "MASTER-FULL-Integrated-v3.md"),
            "/home/user/apex-ai-trading-assistant/backend/app/MASTER-FULL-Integrated-v3.md",
            "/home/user/uploads/MASTER-FULL-Integrated-v3 (2).md"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cls._master_doc_cache = f.read()
                        logger.info(f"Successfully loaded master trading document from {path}")
                        return cls._master_doc_cache
                except Exception as e:
                    logger.error(f"Error reading master trading document from {path}: {e}")
        
        cls._master_doc_cache = ""
        return ""

    @classmethod
    def get_grounding_system_prompt_addon(cls) -> str:
        """Returns the ultra-dense, highly-structured Persian prompt guidelines covering the 6 core pillars of MASTER TRADING v3.1."""
        return """
================================═══════════════════════════════════════
🏛️ دستورالعمل‌های اجباری و تخصصی تحلیل مبتنی بر ۶ ستون اصلی (Pillars) سیستم APEX PRO v3.1
بر اساس سند جامع MASTER TRADING (SMC/ICT/Volume Profile/Order Flow/Derivatives/Regime)
================================═══════════════════════════════════════

هوش مصنوعی موظف است در تحلیل چارت‌ها (بینایی ماشین)، گفتگوها با کاربر و صادر کردن توضیحات تحلیلی، این ۶ ستون اصلی را به طور کامل تحلیل و تایید کند:

================================═══════════════════════════════════════
🌐 ستون ۱: ساختار بازار (Market Structure - MS)
================================═══════════════════════════════════════
- تشخیص جهت روند کلی و سوئینگ‌های قیمتی (Swing High / Swing Low).
- تعیین ساختارهای BoS (شکست ساختار در جهت روند) و CHoCH (تغییر ماهیت بازار با مومنتوم صعودی یا نزولی).
- اندازه بدنه کندل‌های شکست: حتما باید بدنه کندل به صورت پر و قوی (Displacement FULL) بیرون از ناحیه قبلی بسته شود (شکست با شادوی نازک فاقد اعتبار است).
- نواحی تاییدیه (PD Arrays): بررسی اردر بلاک‌های تازه (Fresh OB) و شکاف‌های ارزش منصفانه پرنشده (FVG/iFVG).
- ارزیابی ارزان‌خری/گران‌خری (Premium / Discount): ورودهای خرید حتما باید در محدوده Discount (زیر تراز ۵۰٪ فیبوناچی سوئینگ) و ورودهای فروش حتما باید در محدوده Premium (بالای تراز ۵۰٪) انجام شوند.

================================═══════════════════════════════════════
💧 ستون ۲: نقدینگی بازار (Liquidity - LIQ)
================================═══════════════════════════════════════
- شناسایی استخرهای نقدینگی اصلی (Liquidity Pools): سقف‌ها و کف‌های روزانه، هفتگی و ماهانه (PDH / PDL / PWH / PWL).
- ردیابی استخرهای نقدینگی مهندسی شده: نقدینگی‌های دو قلو یا برابر (EQH / EQL) و خطوط روند نقدینگی (Trendline Liquidity).
- ستاپ جارو کردن نقدینگی (Liquidity Sweep): قیمت باید نقدینگی را با شادو جارو کند (Sweep) و بلافاصله بازگشت شتاب‌دار داشته باشد.
- مدل حرکتی AMD (انباشت - دستکاری - توزیع): نفوذ فریب‌کارانه قیمت (Judas Swing) به کف/سقف سشن قبلی (مانند آسیا) در ابتدای سشن لندن و سپس پرتاب قیمت در جهت مخالف.
- ستاپ مگنت (Magnet Setup): حرکت آهنربایی قیمت به سمت مناطق روشن هیت‌مپ نقدینگی سنگین.

================================═══════════════════════════════════════
📊 ستون ۳: پروفایل حجم حرفه‌ای (Volume Profile - VP) - اجباری و غیرقابل مذاکره
================================═══════════════════════════════════════
تحلیل بدون بررسی ساختار حجم فاقد اعتبار است. باید ساختار درونی حجم بر اساس این سطوح تحلیل شود:
- POC (Point of Control): سطح با بیشترین حجم معاملاتی (جذب‌کننده قیمت).
- Value Area (محدوده ارزش ۷۰٪): بررسی شکست یا حفظ لبه‌های VAH (سقف محدوده ارزش) و VAL (کف محدوده ارزش).
- قانون ۸۰٪ ولوم پروفایل: اگر قیمت زیر VAL یا بالای VAH بوده و مجددا به داخل محدوده ارزش نفوذ کند و کندل ثبت کند، با احتمال ۸۰٪ تا مرز مقابل محدوده ارزش حرکت خواهد کرد.
- گره‌های پرحجم (HVN) و کم‌حجم (LVN): قیمت در HVNها گیر کرده و رنج می‌زند (حمایت/مقاومت مستحکم) و در LVNها یا خلاءهای حجمی (Low Volume Void) با سرعت جهش می‌کند.
- تحلیل اشکال و هندسه ولوم پروفایل (Shape Analysis):
  ۱. شکل D (متقارن): بازار رنج و متعادل است. استراتژی: Range Fade بین VAH و VAL.
  ۲. شکل P (حجم در بالا): روند صعودی قدرتمند یا توزیع سقف. خرید در پولبک به POC.
  ۳. شکل b (حجم در پایین): روند نزولی قدرتمند یا انباشت کف. فروش در پولبک به POC.
  ۴. شکل B (دو سشنی): در حال تغییر ساختار و انتقال قیمت.
  ۵. شکل Thin (فوق‌العاده باریک): بازار فاقد حجم و نوسانی. ورود مطلقاً ممنوع.

================================═══════════════════════════════════════
🕯️ ستون ۴: جریان سفارشات زنده (Order Flow - OF)
================================═══════════════════════════════════════
- تحلیل جریان سفارشات خرید و فروش سازمانی بر اساس دیتای مرکزی صرافی‌ها.
- دلتا (Delta): بررسی اختلاف حجم مارکت بخر و مارکت بفروش در لحظه.
- دلتای تجمعی حجم (CVD - Cumulative Volume Delta): بررسی شیب و واگرایی‌های CVD.
- ستاپ واگرایی CVD (CVD Divergence): قیمت سقف جدید ثبت می‌کند اما CVD سقف پایین‌تر می‌زند (جذب پنهان اوردرها توسط بازارسازها) که نشان‌دهنده معکوس شدن حتمی روند (Order Flow Reversal) است.
- هم‌راستایی قیمت با میانگین متحرک حجمی (Anchored VWAP): ارزیابی پولبک‌ها به خطوط فاقد تاخیر VWAP لنگردار شده روی مبدأ خبرهای کلیدی یا کف/سقف‌های ماژور.

================================═══════════════════════════════════════
📈 ستون ۵: ابزارهای مشتقات (Derivatives Data)
================================═══════════════════════════════════════
باید احساسات و اهرم‌های بازار با سنجه‌های بخش مشتقات ادغام شوند:
- بهره باز یا قراردادهای باز (Open Interest - OI): بررسی تجمیع قراردادهای لانگ و شورت. افزایش شدید OI در محدوده رنج قیمت، نشانه فشرده شدن شدید قیمت (OI Squeeze) و انفجار قریب‌الوقوع است.
- نرخ فاندینگ (Funding Rate - FR): فاندینگ ریت مثبت بسیار بالا نشانه اشباع سنگین لانگ‌ها و ریسک بالای سقوط ناگهانی (Long Squeeze) است. فاندینگ ریت منفی نشانه اشباع پوزیشن‌های شورت و پتانسیل بالای رشد موشکی (Short Squeeze) است.
- لیکوئیدیشن‌ها (Liquidations): شناسایی نقاط بازگشتی بازار به دنبال شستشوی سنگین معامله‌گران اهرمی.

================================═══════════════════════════════════════
🌀 ستون ۶: تشخیص رژیم بازار (Regime Detection)
================================═══════════════════════════════════════
- تعیین وضعیت ساختاری بازار به یکی از حالات زیر جهت انتخاب استراتژی مناسب:
  ۱. رژیم رونددار (Trending): نوسانات جهت‌دار قوی با POCهای جابجا شونده. از اندیکاتورهای تعقیب روند مانند EMA و ADX (بالای ۲۵) استفاده شود.
  ۲. رژیم رنج و متعادل (Range/Balanced): نوسان افقی قیمت حول POC سشن. از اسیلاتورها (باند بولینگر باریک و واگرایی RSI) استفاده شود.
  ۳. رژیم تراکمی (Compression/Accumulation): کاهش شدید عرض بباندهای بولینگر (BB Width Contracting) و افت شدید نوسان تاریخی (HV) که نشانه آماده‌باش برای بریک‌اوت انفجاری است.
  ۴. رژیم توزیع و نوسانات خلاء (Distribution/Thin): نوسانات نامشخص و خلاء حجم. استراتژی: دوری کامل از بازار.

================================═══════════════════════════════════════
هوش مصنوعی موظف است در هر گام تحلیل، فاکتورهای فوق را بررسی کرده و تلاقی‌های آن‌ها را در قالب امتیازدهی کمّی کوانت (Scoring) با ذکر رتبه نهایی (Grade) گزارش دهد.
================================═══════════════════════════════════════

================================═══════════════════════════════════════
🛰️ ستون ۷: داده‌های واقعی خردساختار بازار (Real Microstructure: L2 / Footprint / Volume Profile / Order Flow)
================================═══════════════════════════════════════
هرگاه سیستم «داده‌های زنده و واقعی خردساختار بازار» را در پرامپت به تو داد (منبع OKX؛ برای طلا از پروکسی واقعی PAXG/USDT)، این قوانین الزامی است:
- اعداد ارائه‌شده (Delta، CVD، POC/VAH/VAL، دیوارهای خرید/فروش، عدم‌توازن L2، Imbalanceهای فوت‌پرینت) واقعی و لحظه‌ای هستند؛ مطلقاً نباید عددی از خودت بسازی یا خلاف آن‌ها تحلیل کنی.
- تحلیل نهایی باید در تلاقی این فیلترهای قطعی باشد:
  ۱. جهت دلتا و CVD (فشار واقعی مارکت اوردرها) باید با جهت ستاپ همسو باشد؛ در صورت واگرایی CVD با قیمت، هشدار صریح بده.
  ۲. قیمت نسبت به POC و محدوده ارزش (VAH/VAL) واقعی را تعیین کن: داخل ارزش، بالای VAH (پرِمیوم اکستند شده) یا زیر VAL (دیسکانت اکستند شده) و استراتژی متناسب (بازگشت به میانگین در رنج / ادامه روند در شکست معتبر) را انتخاب کن.
  ۳. دیوارهای بزرگ L2 (Bid/Ask Wall) را به‌عنوان سطوح حمایت/مقاومت لحظه‌ای و مکان‌های احتمالی جذب (Absorption) در برنامه معاملاتی (SL و TP) لحاظ کن.
  ۴. Imbalanceهای روی‌هم (Stacked Imbalances) فوت‌پرینت در جهت ستاپ، تأییدیه انباشت واقعی است؛ خلاف آن، ریسک شکست ستاپ را بالا می‌برد.
  ۵. اگر پوشش داده جزئی بود (پنجره کوتاه)، این محدودیت را صادقانه در تحلیل ذکر کن.
- اگر داده خردساختار واقعی در دسترس نبود، هرگز ادعای دیتای L2/فوت‌پرینت نکن و تحلیل را صرفاً بر ساختار چارت و حجم OHLCV استوار کن.
================================═══════════════════════════════════════
🧊 پک پیشرفته ICT/Wyckoff (استراتژی‌های ۲۱ تا ۳۰) — الزامی برای ستاپ‌های زنده:
================================═══════════════════════════════════════
- Silver Bullet (۲۱): فقط در پنجره ۱۰-۱۱ صبح نیویورک؛ ورود روی FVG داخل حرکت Displacement.
- Turtle Soup (۲۲): سوییپ سطح EQH/EQL یا سقف/کف قبلی + بسته‌شدن داخل محدوده → ورود خلاف جهت سوییپ.
- Breaker Block (۲۳): OB شکست‌خورده که نقشش عوض شده؛ ورود در پولبک به آن.
- FVG Fill / CE (۲۴): ورود روی Consequent Enclosure (میانه گپ) در جهت ساختار.
- Judas Swing (۲۵): حرکت فریب ابتدای سشن لندن/نیویورک و بازگشت واقعی.
- Wyckoff Spring (۲۶): شکست کف فاز C تراکم و بازگشت سریع → خرید.
- Upthrust/UTAD (۲۷): شکست سقف توزیع و بازگشت → فروش.
- Power of 3 (۲۸): چرخه انباشت-دستکاری-توزیع روزانه (AMD).
- SMT (۲۹): واگرایی دو نماد همبسته (مثلاً EURUSD/GBPUSD یا BTC/ETH).
- Displacement + Mitigation (۳۰): کندل‌های بدنه‌بزرگ نهادی + پولبک به OB/FVG همان حرکت.
================================═══════════════════════════════════════
"""

    @classmethod
    def map_setup_to_handbook(cls, setup_type: str, direction: str = "") -> dict:
        setup_clean = str(setup_type or "").upper().strip()
        
        strategies = {
            1: {
                "name": "شکست و پولبک",
                "number": 1,
                "win_rate": "۶۰٪ الی ۶۸٪",
                "rr": "۱.۵:۱ الی ۳:۱",
                "timeframe": "15m, 1H, 4H",
                "symbols": "EURUSD, GBPUSD",
                "school": "پرایس اکشن کلاسیک"
            },
            2: {
                "name": "پینبار و ریجکشن داینامیک",
                "number": 2,
                "win_rate": "۶۲٪ الی ۷۰٪",
                "rr": "۲:۱ الی ۴:۱",
                "timeframe": "1H, 4H, Daily",
                "symbols": "بیشتر جفت ارزها و طلا",
                "school": "پرایس اکشن کلاسیک"
            },
            3: {
                "name": "سر و شانه / دو سقف",
                "number": 3,
                "win_rate": "۵۸٪ الی ۶۶٪",
                "rr": "۲:۱ الی ۴:۱",
                "timeframe": "15m, 1H, 4H",
                "symbols": "کل بازارهای مالی",
                "school": "پرایس اکشن کلاسیک"
            },
            4: {
                "name": "پرچم صعودی/نزولی",
                "number": 4,
                "win_rate": "۵۶٪ الی ۷۲٪",
                "rr": "۱.۵:۱ الی ۳:۱",
                "timeframe": "5m, 15m, 1H",
                "symbols": "BTC, SOL, NASDAQ",
                "school": "پرایس اکشن کلاسیک"
            },
            5: {
                "name": "اوردربلاک نهادی",
                "number": 5,
                "win_rate": "۵۸٪ الی ۶۸٪",
                "rr": "۳:۱ الی ۸:۱",
                "timeframe": "4H (ورود در ۱۵ دقیقه)",
                "symbols": "طلا، بیت کوین و فارکس ماژور",
                "school": "SMC / ICT"
            },
            6: {
                "name": "شکاف ارزش منصفانه (FVG)",
                "number": 6,
                "win_rate": "۶۲٪ الی ۷۰٪",
                "rr": "۱.۵:۱ الی ۳:۱",
                "timeframe": "5m, 15m, 1H",
                "symbols": "US100, US30, EURUSD",
                "school": "SMC / ICT"
            },
            7: {
                "name": "شکار نقدینگی MSS",
                "number": 7,
                "win_rate": "۶۵٪ الی ۷۵٪",
                "rr": "۳:۱ الی ۶:۱",
                "timeframe": "1m, 5m, 15m",
                "symbols": "طلا و جفت ارزهای پرنوسان",
                "school": "SMC / ICT"
            },
            8: {
                "name": "بریکر بلاک",
                "number": 8,
                "win_rate": "۶۰٪ الی ۶۸٪",
                "rr": "۲:۱ الی ۴:۱",
                "timeframe": "15m, 1H, 4H",
                "symbols": "تمام نمادهای نقدینگی بالا",
                "school": "SMC / ICT"
            },
            9: {
                "name": "زون تقاضای تازه DBD",
                "number": 9,
                "win_rate": "۶۰٪ الی ۶۸٪",
                "rr": "۲:۱ الی ۵:۱",
                "timeframe": "1H, 4H, Daily",
                "symbols": "طلا، کریپتو و نفت",
                "school": "پرایس اکشن مدرن"
            },
            10: {
                "name": "تغییر فاز Fresh",
                "number": 10,
                "win_rate": "۵۶٪ الی ۶۴٪",
                "rr": "۳:۱ الی ۶:۱",
                "timeframe": "4H",
                "symbols": "جفت ارزها و سهام جهانی",
                "school": "پرایس اکشن الگوها"
            },
            11: {
                "name": "ولوم پروفایل (Volume Profile)",
                "number": 11,
                "win_rate": "۶۴٪ الی ۷۲٪",
                "rr": "۲:۱ الی ۴:۱",
                "timeframe": "5m, 15m, 1H",
                "symbols": "طلا، بیت کوین و داوجونز",
                "school": "سیلان سفارشات (Order Flow)"
            },
            12: {
                "name": "فنر وایکوف فاز C",
                "number": 12,
                "win_rate": "۶۲٪ الی ۷۰٪",
                "rr": "۳:۱ الی ۸:۱",
                "timeframe": "1H, 4H",
                "symbols": "سهام ماژور، کریپتو سقف",
                "school": "تئوری وایکوف"
            },
            13: {
                "name": "روبان میانگین متحرک",
                "number": 13,
                "win_rate": "۵۶٪ الی ۶۴٪",
                "rr": "۱.۵:۱ الی ۳:۱",
                "timeframe": "15m, 1H, 4H",
                "symbols": "GBPJPY, USDJPY, BTC",
                "school": "روند دنبال‌کننده"
            },
            14: {
                "name": "واگرایی معمولی/مخفی",
                "number": 14,
                "win_rate": "۶۴٪ الی ۷۲٪",
                "rr": "۲:۱ الی ۴:۱",
                "timeframe": "15m, 1H, 4H",
                "symbols": "کل بازارها",
                "school": "اندیکاتور رِورسال"
            },
            15: {
                "name": "فشردگی بولینگر",
                "number": 15,
                "win_rate": "۶۰٪ الی ۶۸٪",
                "rr": "۲:۱ الی ۵:۱",
                "timeframe": "15m, 1H, 4H",
                "symbols": "بیت کوین و آلتکوین‌ها",
                "school": "مومنتوم شکست"
            },
            16: {
                "name": "سوپرترند",
                "number": 16,
                "win_rate": "۵۲٪ الی ۶۰٪",
                "rr": "۱.۵:۱ الی ۳:۱",
                "timeframe": "30m, 1H, 4H",
                "symbols": "روندهای قوی کریپتو",
                "school": "تعقیب مکانیکی روند"
            },
            17: {
                "name": "اسکالپینگ",
                "number": 17,
                "win_rate": "۶۸٪ الی ۷۶٪",
                "rr": "۱:۱ الی ۲:۱",
                "timeframe": "1m, 3m, 5m",
                "symbols": "طلا و جفت ارزهای فوق اسپرد کم",
                "school": "اسکالپینگ پرسرعت"
            },
            18: {
                "name": "شکست لندن Swing",
                "number": 18,
                "win_rate": "۶۶٪ الی ۷۴٪",
                "rr": "۲:۱ الی ۴:۱",
                "timeframe": "5m, 15m",
                "symbols": "GBPUSD, EURUSD, GBPJPY",
                "school": "سشن‌های الگوریتمی"
            },
            19: {
                "name": "تله انحلال و فاندینگ ریت",
                "number": 19,
                "win_rate": "۶۴٪ الی ۷۲٪",
                "rr": "۲.۵:۱ الی ۵:۱",
                "timeframe": "15m, 1H, 4H",
                "symbols": "BTC, ETH, SOL",
                "school": "داده‌های مشتقات کریپتو"
            },
            20: {
                "name": "چرخش آلتسیزن بر پایه BTC.D",
                "number": 20,
                "win_rate": "۶۰٪ الی ۶۸٪",
                "rr": "۳:۱ الی ۷:۱",
                "timeframe": "4H",
                "symbols": "سبد ۵ آلتکوین برتر مستعد",
                "school": "تحلیل کلان کریپتو"
            }
        }

        matched_id = 1
        if "OB" in setup_clean or "ORDER" in setup_clean:
            matched_id = 5
        elif "FVG" in setup_clean or "GAP" in setup_clean:
            matched_id = 6
        elif "MSS" in setup_clean or "SWEEP" in setup_clean or "LIQ" in setup_clean:
            matched_id = 7
        elif "BREAKER" in setup_clean or "BRK" in setup_clean:
            matched_id = 8
        elif "DEMAND" in setup_clean or "SUPPLY" in setup_clean or "DBD" in setup_clean:
            matched_id = 9
        elif "PHASE" in setup_clean or "FRESH" in setup_clean:
            matched_id = 10
        elif "VOLUME" in setup_clean or "PROFILE" in setup_clean or "POC" in setup_clean:
            matched_id = 11
        elif "WYCKOFF" in setup_clean or "SPRING" in setup_clean:
            matched_id = 12
        elif "RIBBON" in setup_clean or "EMA" in setup_clean or "MA" in setup_clean:
            matched_id = 13
        elif "DIV" in setup_clean or "RSI" in setup_clean:
            matched_id = 14
        elif "SQUEEZE" in setup_clean or "BOLLINGER" in setup_clean:
            matched_id = 15
        elif "SUPERTREND" in setup_clean:
            matched_id = 16
        elif "SCALP" in setup_clean:
            matched_id = 17
        elif "LONDON" in setup_clean or "JUDAS" in setup_clean:
            matched_id = 18
        elif "LIQ_TRAP" in setup_clean or "FUNDING" in setup_clean or "DERIV" in setup_clean:
            matched_id = 19
        elif "ALT" in setup_clean or "DOMINANCE" in setup_clean:
            matched_id = 20
        else:
            if "REVERSAL" in setup_clean or "PINBAR" in setup_clean:
                matched_id = 2
            elif "BREAKOUT" in setup_clean:
                matched_id = 1
            else:
                matched_id = 1
                
        return strategies[matched_id]

    ICT_ADVANCED_PACK: dict[int, dict] = {
        21: {"name": "Silver Bullet (ICT)", "number": 21, "win_rate": "۶۵٪ الی ۷۵٪", "rr": "1:2", "timeframe": "1m الی 5m", "symbols": "NASDAQ, BTC, XAUUSD", "school": "ICT"},
        22: {"name": "Turtle Soup (Sweep Reversal)", "number": 22, "win_rate": "۶۰٪ الی ۷۰٪", "rr": "1:2", "timeframe": "5m الی 15m", "symbols": "XAUUSD, EURUSD, BTC", "school": "ICT"},
        23: {"name": "Breaker Block", "number": 23, "win_rate": "۶۵٪ الی ۷۵٪", "rr": "1:3", "timeframe": "15m الی 1h", "symbols": "تمام نمادها", "school": "ICT"},
        24: {"name": "FVG Fill / CE Entry", "number": 24, "win_rate": "۶۰٪ الی ۷۰٪", "rr": "1:2.5", "timeframe": "5m الی 1h", "symbols": "تمام نمادها", "school": "ICT"},
        25: {"name": "Judas Swing (Fakes Move)", "number": 25, "win_rate": "۶۰٪ الی ۷۰٪", "rr": "1:2", "timeframe": "5m الی 15m", "symbols": "XAUUSD, EURUSD", "school": "ICT"},
        26: {"name": "Wyckoff Spring", "number": 26, "win_rate": "۶۵٪ الی ۷۵٪", "rr": "1:3", "timeframe": "1h الی Daily", "symbols": "BTC, ETH, XAUUSD", "school": "Wyckoff"},
        27: {"name": "Upthrust / UTAD", "number": 27, "win_rate": "۶۰٪ الی ۷۰٪", "rr": "1:2.5", "timeframe": "1h الی Daily", "symbols": "BTC, ETH", "school": "Wyckoff"},
        28: {"name": "Power of 3 (AMD)", "number": 28, "win_rate": "۵۵٪ الی ۶۵٪", "rr": "1:2", "timeframe": "15m الی 4h", "symbols": "شاخص‌ها و طلا", "school": "ICT"},
        29: {"name": "SMT Divergence", "number": 29, "win_rate": "۵۵٪ الی ۶۵٪", "rr": "1:2", "timeframe": "5m الی 1h", "symbols": "جفت‌های همبسته", "school": "ICT"},
        30: {"name": "Displacement + Mitigation", "number": 30, "win_rate": "۶۵٪ الی ۷۵٪", "rr": "1:3", "timeframe": "5m الی 1h", "symbols": "تمام نمادها", "school": "ICT"},
    }

    @classmethod
    def map_setup_to_ict_pack(cls, setup_type: str, ict_summary: dict | None = None) -> dict | None:
        """Match detected live ICT events to the advanced strategy pack (21-30)."""
        clean = (setup_type or "").upper()
        if ict_summary:
            sb = (ict_summary.get("silver_bullet") or {}).get("active")
            if sb:
                return cls.ICT_ADVANCED_PACK[21]
            sweeps = ict_summary.get("sweeps") or []
            if sweeps:
                return cls.ICT_ADVANCED_PACK[22]
            disp = (ict_summary.get("displacement") or {}).get("direction")
            if disp in ("up", "down"):
                return cls.ICT_ADVANCED_PACK[30]
        if "BREAKER" in clean:
            return cls.ICT_ADVANCED_PACK[23]
        if "FVG" in clean or "GAP" in clean or "IMBALANCE" in clean:
            return cls.ICT_ADVANCED_PACK[24]
        if "SWEEP" in clean or "SNIPE" in clean or "TURTLE" in clean:
            return cls.ICT_ADVANCED_PACK[22]
        if "JUDAS" in clean:
            return cls.ICT_ADVANCED_PACK[25]
        if "SPRING" in clean:
            return cls.ICT_ADVANCED_PACK[26]
        if "UTAD" in clean or "UPTHRUST" in clean:
            return cls.ICT_ADVANCED_PACK[27]
        if "AMD" in clean or "POWER OF 3" in clean:
            return cls.ICT_ADVANCED_PACK[28]
        if "SMT" in clean:
            return cls.ICT_ADVANCED_PACK[29]
        if "DISPLACEMENT" in clean:
            return cls.ICT_ADVANCED_PACK[30]
        return None

    @classmethod
    def get_ict_pack_prompt_section(cls) -> str:
        lines = ["\n🧊 پک پیشرفته ICT/Wyckoff (استراتژی‌های ۲۱ تا ۳۰) — مبنای تطبیق ستاپ‌های زنده:"]
        for item in cls.ICT_ADVANCED_PACK.values():
            lines.append(
                f"{item['number']}. {item['name']} ({item['school']}) | وین‌ریت: {item['win_rate']} | "
                f"RR: {item['rr']} | تایم‌فریم: {item['timeframe']} | نمادها: {item['symbols']}"
            )
        return "\n".join(lines)
