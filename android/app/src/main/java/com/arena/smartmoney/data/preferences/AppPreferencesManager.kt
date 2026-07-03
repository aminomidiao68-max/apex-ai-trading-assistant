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

    companion object {
        private const val KEY_NOTIFICATIONS = "notifications_enabled"
        private const val KEY_AUTO_REFRESH = "auto_refresh_enabled"
        private const val KEY_TESTNET_ONLY = "testnet_only"
        private const val KEY_RISK_ACK = "risk_ack"
        private const val KEY_LANGUAGE = "language"
    }
}
