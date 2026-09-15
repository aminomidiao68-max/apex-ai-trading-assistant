package com.arena.smartmoney.data.preferences

import android.content.Context

class AppPreferencesManager(context: Context) {
    private val prefs = context.getSharedPreferences("apex_ai_prefs", Context.MODE_PRIVATE)

    fun isNotificationsEnabled(): Boolean = prefs.getBoolean(KEY_NOTIFICATIONS, true)
    fun setNotificationsEnabled(value: Boolean) = prefs.edit().putBoolean(KEY_NOTIFICATIONS, value).apply()

    fun isAutoRefreshEnabled(): Boolean = prefs.getBoolean(KEY_AUTO_REFRESH, true)
    fun setAutoRefreshEnabled(value: Boolean) = prefs.edit().putBoolean(KEY_AUTO_REFRESH, value).apply()

    fun isTestnetOnlyEnabled(): Boolean = prefs.getBoolean(KEY_TESTNET_ONLY, true)
    fun setTestnetOnlyEnabled(value: Boolean) = prefs.edit().putBoolean(KEY_TESTNET_ONLY, value).apply()

    fun isRiskAcknowledged(): Boolean = prefs.getBoolean(KEY_RISK_ACK, false)
    fun setRiskAcknowledged(value: Boolean) = prefs.edit().putBoolean(KEY_RISK_ACK, value).apply()

    fun getLanguage(): String = prefs.getString(KEY_LANGUAGE, "fa") ?: "fa"
    fun setLanguage(value: String) = prefs.edit().putString(KEY_LANGUAGE, value).apply()

    // ---------------- chart user settings (v3.11) ----------------
    fun getChartSymbol(): String = prefs.getString(KEY_CHART_SYMBOL, "XAUUSD") ?: "XAUUSD"
    fun setChartSymbol(value: String) = prefs.edit().putString(KEY_CHART_SYMBOL, value).apply()

    fun getChartMarket(): String = prefs.getString(KEY_CHART_MARKET, "") ?: ""
    fun setChartMarket(value: String) = prefs.edit().putString(KEY_CHART_MARKET, value).apply()

    fun getChartTimeframe(): String = prefs.getString(KEY_CHART_TIMEFRAME, "15m") ?: "15m"
    fun setChartTimeframe(value: String) = prefs.edit().putString(KEY_CHART_TIMEFRAME, value).apply()

    fun getChartCompareSymbols(): List<String> =
        (prefs.getString(KEY_CHART_COMPARE, "") ?: "")
            .split(",")
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .take(2)

    fun setChartCompareSymbols(value: List<String>) =
        prefs.edit().putString(KEY_CHART_COMPARE, value.joinToString(",")).apply()

    fun isProximityAlertsEnabled(): Boolean = prefs.getBoolean(KEY_PROXIMITY_ALERTS, true)
    fun setProximityAlertsEnabled(value: Boolean) = prefs.edit().putBoolean(KEY_PROXIMITY_ALERTS, value).apply()

    fun isClassicLevelsEnabled(): Boolean = prefs.getBoolean(KEY_CLASSIC_LEVELS, true)
    fun setClassicLevelsEnabled(value: Boolean) = prefs.edit().putBoolean(KEY_CLASSIC_LEVELS, value).apply()

    companion object {
        private const val KEY_NOTIFICATIONS = "notifications_enabled"
        private const val KEY_AUTO_REFRESH = "auto_refresh_enabled"
        private const val KEY_TESTNET_ONLY = "testnet_only"
        private const val KEY_RISK_ACK = "risk_ack"
        private const val KEY_LANGUAGE = "language"
        private const val KEY_CHART_SYMBOL = "chart_symbol"
        private const val KEY_CHART_MARKET = "chart_market"
        private const val KEY_CHART_TIMEFRAME = "chart_timeframe"
        private const val KEY_CHART_COMPARE = "chart_compare_symbols"
        private const val KEY_PROXIMITY_ALERTS = "proximity_alerts_enabled"
        private const val KEY_CLASSIC_LEVELS = "chart_classic_levels_enabled"
    }
}
