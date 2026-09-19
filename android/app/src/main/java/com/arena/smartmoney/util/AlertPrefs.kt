package com.arena.smartmoney.util

import android.content.Context

/**
 * Single source of truth for the tier-alert watchlist and the user's
 * notification preferences (v3.31 alert settings). All decisions stay on the
 * deterministic backend — these prefs only control WHAT gets notified.
 * v3.32: expanded from 11 to 20 symbols (crypto majors + forex majors + indices)
 * for broader coverage without relaxing any gate. Probable scan now covers 20.
 */
object AlertPrefs {
    private const val PREFS = "tier_alert_prefs"

    val watchlist: List<Triple<String, String, String>> = listOf(
        // crypto majors (1h) — 7
        Triple("BTCUSDT", "crypto", "1h"),
        Triple("ETHUSDT", "crypto", "1h"),
        Triple("SOLUSDT", "crypto", "1h"),
        Triple("XRPUSDT", "crypto", "1h"),
        Triple("BNBUSDT", "crypto", "1h"),
        Triple("AVAXUSDT", "crypto", "1h"),
        Triple("DOGEUSDT", "crypto", "1h"),
        // forex & metals (1h) — 10
        Triple("XAUUSD", "", "1h"),
        Triple("XAGUSD", "", "1h"),
        Triple("EURUSD", "", "1h"),
        Triple("GBPUSD", "", "1h"),
        Triple("USDJPY", "", "1h"),
        Triple("GBPJPY", "", "1h"),
        Triple("AUDUSD", "", "1h"),
        Triple("NZDUSD", "", "1h"),
        Triple("USDCAD", "", "1h"),
        Triple("USDCHF", "", "1h"),
        // indices & energy (1h) — 3
        Triple("USOIL", "", "1h"),
        Triple("US100", "", "1h"),
        Triple("US30", "", "1h"),
    )

    val allSymbols: Set<String> = watchlist.map { it.first }.toSet()

    private fun p(c: Context) = c.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun alertsEnabled(c: Context): Boolean = p(c).getBoolean("alerts_enabled", true)
    fun setAlertsEnabled(c: Context, v: Boolean) { p(c).edit().putBoolean("alerts_enabled", v).apply() }

    fun notifyHighConfidence(c: Context): Boolean = p(c).getBoolean("notify_high", true)
    fun setNotifyHighConfidence(c: Context, v: Boolean) { p(c).edit().putBoolean("notify_high", v).apply() }

    fun notifyProb70(c: Context): Boolean = p(c).getBoolean("notify_prob70", false)
    fun setNotifyProb70(c: Context, v: Boolean) { p(c).edit().putBoolean("notify_prob70", v).apply() }

    fun symbols(c: Context): Set<String> =
        p(c).getStringSet("symbols", allSymbols)?.toSet() ?: allSymbols

    fun setSymbols(c: Context, s: Set<String>) { p(c).edit().putStringSet("symbols", s).apply() }
}
