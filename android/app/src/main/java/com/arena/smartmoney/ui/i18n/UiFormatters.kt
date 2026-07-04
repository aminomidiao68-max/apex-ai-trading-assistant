package com.arena.smartmoney.ui.i18n

import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

fun localizeSessionName(value: String, t: (String, String) -> String): String {
    return when (value.lowercase(Locale.getDefault())) {
        "off session", "off-session" -> t("Off Session", "خارج از سشن")
        "london" -> t("London", "لندن")
        "new york" -> t("New York", "نیویورک")
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
        value.contains("Bearish FVG present", ignoreCase = true) -> t("Bearish imbalance zone detected", "ناحیه عدم تعادل نزولی شناسایی شد")
        value.contains("Bullish FVG present", ignoreCase = true) -> t("Bullish imbalance zone detected", "ناحیه عدم تعادل صعودی شناسایی شد")
        value.contains("Off-session conditions reduce setup quality", ignoreCase = true) -> t("Off-session conditions reduce setup quality", "خارج از سشن بودن کیفیت ستاپ را کاهش می‌دهد")
        value.contains("Price above EMA20/EMA50 with bullish structure", ignoreCase = true) -> t("Price above EMA20/EMA50 with bullish structure", "قیمت بالای EMA20/EMA50 و ساختار صعودی است")
        value.contains("Price below EMA20/EMA50 with bearish structure", ignoreCase = true) -> t("Price below EMA20/EMA50 with bearish structure", "قیمت پایین EMA20/EMA50 و ساختار نزولی است")
        value.contains("Bullish multi-layer confluence confirmed", ignoreCase = true) -> t("Bullish multi-layer confluence confirmed", "همگرایی چندلایه صعودی تأیید شد")
        value.contains("Bearish multi-layer confluence confirmed", ignoreCase = true) -> t("Bearish multi-layer confluence confirmed", "همگرایی چندلایه نزولی تأیید شد")
        value.contains("Volatility and session conditions support execution", ignoreCase = true) -> t("Volatility and session conditions support execution", "نوسان و شرایط سشن از اجرای معامله حمایت می‌کنند")
        value.contains("Active trading session", ignoreCase = true) -> t("Active trading session", "سشن معاملاتی فعال")
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
