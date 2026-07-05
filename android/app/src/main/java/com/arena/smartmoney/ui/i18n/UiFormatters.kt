package com.arena.smartmoney.ui.i18n

import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

fun localizeSessionName(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "off session", "off-session" -> t("Off Session", "خارج از سشن")
        "london" -> t("London", "لندن")
        "new york", "newyork" -> t("New York", "نیویورک")
        "london-new york overlap", "london-newyork overlap" -> t("London-New York Overlap", "همپوشانی لندن-نیویورک")
        "asia", "asian" -> t("Asia", "آسیا")
        else -> value
    }
}

fun localizeMarketQuality(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "high" -> t("High", "بالا")
        "medium" -> t("Medium", "متوسط")
        "low" -> t("Low", "پایین")
        else -> value
    }
}

fun localizeBackendStatus(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "connected" -> t("Connected", "متصل")
        "streaming" -> t("Streaming", "در حال استریم")
        "live-fallback" -> t("Live Fallback", "جایگزین زنده")
        "waiting_for_backend" -> t("Waiting for Backend", "در انتظار بک‌اند")
        "missing_api_key" -> t("Missing API Key", "کلید API موجود نیست")
        "offline" -> t("Offline", "آفلاین")
        "error" -> t("Error", "خطا")
        else -> value
    }
}

fun localizeSignalReason(value: String, t: (String, String) -> String): String {
    return when {
        value.contains("Mixed structure", ignoreCase = true) -> t("Mixed structure, no clear trend dominance", "ساختار بازار ترکیبی است و روند غالب واضح نیست")
        value.contains("Price above EMA20/EMA50 with bullish structure", ignoreCase = true) -> t("Price above EMA20/EMA50 with bullish structure", "قیمت بالای EMA20 و EMA50 است و ساختار بازار صعودی است")
        value.contains("Price below EMA20/EMA50 with bearish structure", ignoreCase = true) -> t("Price below EMA20/EMA50 with bearish structure", "قیمت پایین EMA20 و EMA50 است و ساختار بازار نزولی است")
        value.contains("Fast EMA stack confirms bullish continuation", ignoreCase = true) -> t("Fast EMA stack confirms bullish continuation", "چینش سریع EMA ادامه صعود را تأیید می‌کند")
        value.contains("Fast EMA stack confirms bearish continuation", ignoreCase = true) -> t("Fast EMA stack confirms bearish continuation", "چینش سریع EMA ادامه نزول را تأیید می‌کند")
        value.contains("EMA spread shows strong directional separation", ignoreCase = true) -> t("EMA spread shows strong directional separation", "فاصله EMAها جدایی قدرتمند روند را نشان می‌دهد")
        value.contains("EMA spread shows directional commitment", ignoreCase = true) -> t("EMA spread shows directional commitment", "فاصله EMAها تعهد روند را نشان می‌دهد")
        value.contains("RSI supports bullish momentum", ignoreCase = true) -> t("RSI supports bullish momentum", "RSI از مومنتوم صعودی حمایت می‌کند")
        value.contains("RSI supports bearish momentum", ignoreCase = true) -> t("RSI supports bearish momentum", "RSI از مومنتوم نزولی حمایت می‌کند")
        value.contains("Recent candle pressure favors buyers", ignoreCase = true) -> t("Recent candle pressure favors buyers", "فشار کندل‌های اخیر به نفع خریداران است")
        value.contains("Recent candle pressure favors sellers", ignoreCase = true) -> t("Recent candle pressure favors sellers", "فشار کندل‌های اخیر به نفع فروشندگان است")
        value.contains("Bullish BOS detected", ignoreCase = true) -> t("Bullish BOS detected", "شکست ساختار صعودی شناسایی شد")
        value.contains("Bearish BOS detected", ignoreCase = true) -> t("Bearish BOS detected", "شکست ساختار نزولی شناسایی شد")
        value.contains("Sell-side liquidity sweep and reclaim", ignoreCase = true) -> t("Sell-side liquidity sweep and reclaim", "جمع‌آوری نقدینگی سمت فروش و بازپس‌گیری قیمت دیده شد")
        value.contains("Buy-side liquidity sweep and rejection", ignoreCase = true) -> t("Buy-side liquidity sweep and rejection", "جمع‌آوری نقدینگی سمت خرید و ریجکت قیمت دیده شد")
        value.contains("Bullish CHoCH confirmed after liquidity event", ignoreCase = true) -> t("Bullish CHoCH confirmed after liquidity event", "CHoCH صعودی بعد از رویداد نقدینگی تأیید شد")
        value.contains("Bearish CHoCH confirmed after liquidity event", ignoreCase = true) -> t("Bearish CHoCH confirmed after liquidity event", "CHoCH نزولی بعد از رویداد نقدینگی تأیید شد")
        value.contains("Bullish displacement candle detected", ignoreCase = true) -> t("Bullish displacement candle detected", "کندل جابجایی صعودی شناسایی شد")
        value.contains("Bearish displacement candle detected", ignoreCase = true) -> t("Bearish displacement candle detected", "کندل جابجایی نزولی شناسایی شد")
        value.contains("Equal highs liquidity pool detected", ignoreCase = true) -> t("Equal highs liquidity pool detected", "استخر نقدینگی سقف‌های مساوی شناسایی شد")
        value.contains("Equal lows liquidity pool detected", ignoreCase = true) -> t("Equal lows liquidity pool detected", "استخر نقدینگی کف‌های مساوی شناسایی شد")
        value.contains("Price positioned in discount zone", ignoreCase = true) -> t("Price positioned in discount zone", "قیمت در ناحیه دیسکانت قرار دارد")
        value.contains("Price positioned in premium zone", ignoreCase = true) -> t("Price positioned in premium zone", "قیمت در ناحیه پریمیوم قرار دارد")
        value.contains("Bullish imbalance zone detected", ignoreCase = true) || value.contains("Bullish FVG present", ignoreCase = true) -> t("Bullish imbalance zone detected", "ناحیه عدم تعادل صعودی شناسایی شد")
        value.contains("Bearish imbalance zone detected", ignoreCase = true) || value.contains("Bearish FVG present", ignoreCase = true) -> t("Bearish imbalance zone detected", "ناحیه عدم تعادل نزولی شناسایی شد")
        value.contains("Equal-high liquidity was engineered before bearish rejection", ignoreCase = true) -> t("Equal-high liquidity was engineered before bearish rejection", "پیش از ریجکت نزولی، نقدینگی روی سقف‌های مساوی مهندسی شده بود")
        value.contains("Equal-low liquidity was engineered before bullish reclaim", ignoreCase = true) -> t("Equal-low liquidity was engineered before bullish reclaim", "پیش از بازپس‌گیری صعودی، نقدینگی روی کف‌های مساوی مهندسی شده بود")
        value.contains("Displacement confirms institutional intent", ignoreCase = true) -> t("Displacement confirms institutional intent", "دیسپلیسمنت نیت نهادی بازار را تأیید می‌کند")
        value.contains("Market structure shift improves reversal credibility", ignoreCase = true) -> t("Market structure shift improves reversal credibility", "تغییر ساختار بازار اعتبار برگشت را بیشتر می‌کند")
        value.contains("Buy setup sits in discount zone", ignoreCase = true) -> t("Buy setup sits in discount zone", "ستاپ خرید در ناحیه دیسکانت قرار دارد")
        value.contains("Sell setup sits in premium zone", ignoreCase = true) -> t("Sell setup sits in premium zone", "ستاپ فروش در ناحیه پریمیوم قرار دارد")
        value.contains("Buy setup is entering from premium zone", ignoreCase = true) -> t("Buy setup is entering from premium zone", "ستاپ خرید از ناحیه پریمیوم وارد می‌شود")
        value.contains("Sell setup is entering from discount zone", ignoreCase = true) -> t("Sell setup is entering from discount zone", "ستاپ فروش از ناحیه دیسکانت وارد می‌شود")
        value.contains("Higher timeframe bias is sponsoring buy continuation", ignoreCase = true) -> t("Higher timeframe bias is sponsoring buy continuation", "بایاس تایم‌فریم بالاتر از ادامه حرکت خرید حمایت می‌کند")
        value.contains("Higher timeframe bias is sponsoring sell continuation", ignoreCase = true) -> t("Higher timeframe bias is sponsoring sell continuation", "بایاس تایم‌فریم بالاتر از ادامه حرکت فروش حمایت می‌کند")
        value.contains("Higher timeframe bias confirms buy continuation", ignoreCase = true) -> t("Higher timeframe bias confirms buy continuation", "بایاس تایم‌فریم بالاتر ادامه حرکت خرید را تأیید می‌کند")
        value.contains("Higher timeframe bias confirms sell continuation", ignoreCase = true) -> t("Higher timeframe bias confirms sell continuation", "بایاس تایم‌فریم بالاتر ادامه حرکت فروش را تأیید می‌کند")
        value.contains("Higher timeframe trend disagrees with local setup", ignoreCase = true) -> t("Higher timeframe trend disagrees with local setup", "روند تایم‌فریم بالاتر با ستاپ فعلی همسو نیست")
        value.contains("Lower timeframe execution momentum supports buy continuation", ignoreCase = true) -> t("Lower timeframe execution momentum supports buy continuation", "مومنتوم اجرای تایم‌فریم پایین‌تر از ادامه خرید حمایت می‌کند")
        value.contains("Lower timeframe execution momentum supports sell continuation", ignoreCase = true) -> t("Lower timeframe execution momentum supports sell continuation", "مومنتوم اجرای تایم‌فریم پایین‌تر از ادامه فروش حمایت می‌کند")
        value.contains("Lower timeframe sellers are still pressing against entry", ignoreCase = true) -> t("Lower timeframe sellers are still pressing against entry", "فروشندگان در تایم‌فریم پایین‌تر هنوز روی ناحیه ورود فشار می‌آورند")
        value.contains("Lower timeframe buyers are still pressing against entry", ignoreCase = true) -> t("Lower timeframe buyers are still pressing against entry", "خریداران در تایم‌فریم پایین‌تر هنوز روی ناحیه ورود فشار می‌آورند")
        value.contains("Multi-timeframe confluence boosts conviction", ignoreCase = true) -> t("Multi-timeframe confluence boosts conviction", "همگرایی چندتایم‌فریمی اطمینان ستاپ را بالا می‌برد")
        value.contains("Liquidity sweep and bullish imbalance align", ignoreCase = true) -> t("Liquidity sweep and bullish imbalance align", "سویپ نقدینگی و عدم تعادل صعودی با هم همسو شده‌اند")
        value.contains("Liquidity sweep and bearish imbalance align", ignoreCase = true) -> t("Liquidity sweep and bearish imbalance align", "سویپ نقدینگی و عدم تعادل نزولی با هم همسو شده‌اند")
        value.contains("Bullish order block supports entry zone", ignoreCase = true) -> t("Bullish order block supports entry zone", "اوردر بلاک صعودی از ناحیه ورود حمایت می‌کند")
        value.contains("Bearish order block supports entry zone", ignoreCase = true) -> t("Bearish order block supports entry zone", "اوردر بلاک نزولی از ناحیه ورود حمایت می‌کند")
        value.contains("Bullish multi-layer confluence confirmed", ignoreCase = true) -> t("Bullish multi-layer confluence confirmed", "همگرایی چندلایه صعودی تأیید شد")
        value.contains("Bearish multi-layer confluence confirmed", ignoreCase = true) -> t("Bearish multi-layer confluence confirmed", "همگرایی چندلایه نزولی تأیید شد")
        value.contains("Volatility and session conditions support execution", ignoreCase = true) -> t("Volatility and session conditions support execution", "نوسان و شرایط سشن از اجرای معامله حمایت می‌کنند")
        value.contains("Liquidity map is still shallow for lower timeframe execution", ignoreCase = true) -> t("Liquidity map is still shallow for lower timeframe execution", "نقشه نقدینگی برای اجرای تایم‌فریم پایین هنوز کم‌عمق است")
        value.contains("1m scalping outside prime session reduces quality", ignoreCase = true) -> t("1m scalping outside prime session reduces quality", "اسکالپ 1 دقیقه خارج از سشن اصلی کیفیت را کاهش می‌دهد")
        value.contains("1m trend strength is too weak for high-quality execution", ignoreCase = true) -> t("1m trend strength is too weak for high-quality execution", "قدرت روند در تایم 1 دقیقه برای اجرای باکیفیت ضعیف است")
        value.contains("1m setup has no higher timeframe directional sponsor", ignoreCase = true) -> t("1m setup has no higher timeframe directional sponsor", "ستاپ 1 دقیقه حامی جهت‌دار از تایم بالاتر ندارد")
        value.contains("1m candle pressure is not decisive", ignoreCase = true) -> t("1m candle pressure is not decisive", "فشار کندلی در تایم 1 دقیقه هنوز قاطع نیست")
        value.contains("Lower timeframe outside prime session reduces quality", ignoreCase = true) -> t("Lower timeframe outside prime session reduces quality", "تایم‌فریم پایین خارج از سشن اصلی کیفیت کمتری دارد")
        value.contains("Lower timeframe trend spread is modest", ignoreCase = true) -> t("Lower timeframe trend spread is modest", "فاصله روند در تایم‌فریم پایین محدود است")
        value.contains("Short timeframe volatility is compressed", ignoreCase = true) -> t("Short timeframe volatility is compressed", "نوسان در تایم‌فریم کوتاه فشرده شده است")
        value.contains("1m quality gate blocked execution", ignoreCase = true) -> t("1m quality gate blocked execution", "فیلتر کیفیت 1 دقیقه اجازه اجرا نداد")
        value.contains("Lower timeframe quality gate blocked execution", ignoreCase = true) -> t("Lower timeframe quality gate blocked execution", "فیلتر کیفیت تایم‌فریم پایین اجازه اجرا نداد")
        value.contains("Off-session conditions reduce setup quality", ignoreCase = true) -> t("Off-session conditions reduce setup quality", "خارج از سشن بودن کیفیت ستاپ را کاهش می‌دهد")
        value.contains("High impact news active:", ignoreCase = true) -> t("High impact news active", "خبر پرقدرت فعال است") + ": " + value.substringAfter(":").trim()
        value.contains("Medium impact news near market:", ignoreCase = true) -> t("Medium impact news near market", "خبر با اهمیت متوسط نزدیک بازار است") + ": " + value.substringAfter(":").trim()
        value.contains("Low impact news near market:", ignoreCase = true) -> t("Low impact news near market", "خبر کم‌اهمیت نزدیک بازار است") + ": " + value.substringAfter(":").trim()
        value.contains("Active trading session:", ignoreCase = true) -> {
            val session = localizeSessionName(value.substringAfter(":").trim(), t)
            t("Active trading session", "سشن معاملاتی فعال") + ": $session"
        }
        else -> value
    }
}

fun localizeExecutionLabel(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "execution_ready" -> t("Execution Ready", "آماده اجرا")
        "scalp_ready" -> t("Scalp Ready", "آماده اسکالپ")
        "watchlist" -> t("Watchlist", "تحت نظر")
        "blocked" -> t("Blocked", "مسدود")
        "observe" -> t("Observe", "فقط مشاهده")
        else -> value
    }
}

fun localizeEntryModel(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "bullish order block" -> t("Bullish Order Block", "اوردر بلاک صعودی")
        "bearish order block" -> t("Bearish Order Block", "اوردر بلاک نزولی")
        "bullish imbalance" -> t("Bullish Imbalance", "عدم تعادل صعودی")
        "bearish imbalance" -> t("Bearish Imbalance", "عدم تعادل نزولی")
        "momentum continuation" -> t("Momentum Continuation", "ادامه مومنتوم")
        "no trade" -> t("No Trade", "بدون معامله")
        else -> value
    }
}

fun localizeConfluenceTag(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "htf aligned" -> t("HTF aligned", "همسویی تایم بالاتر")
        "ltf trigger" -> t("LTF trigger", "تریگر تایم پایین")
        "liquidity sweep" -> t("Liquidity sweep", "سویپ نقدینگی")
        "choch" -> t("CHoCH", "CHoCH")
        "displacement" -> t("Displacement", "دیسپلیسمنت")
        "order block" -> t("Order block", "اوردر بلاک")
        "fvg imbalance" -> t("FVG imbalance", "عدم تعادل FVG")
        "discount buy" -> t("Discount buy", "خرید در دیسکانت")
        "premium sell" -> t("Premium sell", "فروش در پریمیوم")
        "prime session" -> t("Prime session", "سشن اصلی")
        else -> value
    }
}

fun localizeRiskFlag(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "high impact news" -> t("High impact news", "خبر پرقدرت")
        "off session" -> t("Off session", "خارج از سشن")
        "htf conflict" -> t("HTF conflict", "تضاد تایم بالاتر")
        "shallow liquidity" -> t("Shallow liquidity", "نقدینگی کم‌عمق")
        "compressed volatility" -> t("Compressed volatility", "فشردگی نوسان")
        "no htf sponsor" -> t("No HTF sponsor", "بدون حامی تایم بالاتر")
        "execution blocked" -> t("Execution blocked", "اجرای ستاپ مسدود شد")
        "daily loss limit reached" -> t("Daily loss limit reached", "حد ضرر روزانه پر شده")
        "maximum trades per day reached" -> t("Maximum trades per day reached", "حداکثر تعداد معاملات روزانه پر شده")
        "maximum consecutive losses reached" -> t("Maximum consecutive losses reached", "حداکثر باخت پیاپی پر شده")
        "maximum open positions reached" -> t("Maximum open positions reached", "حداکثر پوزیشن باز پر شده")
        else -> value
    }
}

fun formatDisplayTimestamp(raw: String): String {
    return runCatching {
        val dt = OffsetDateTime.parse(raw)
        dt.atZoneSameInstant(ZoneId.of("Asia/Tehran"))
            .format(DateTimeFormatter.ofPattern("yyyy/MM/dd • HH:mm", Locale.US))
    }.getOrElse { raw }
}
