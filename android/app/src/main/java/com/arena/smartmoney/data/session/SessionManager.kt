package com.arena.smartmoney.data.session

import android.content.Context
import com.arena.smartmoney.data.network.AuthTokenProvider

class SessionManager(context: Context) {
    private val prefs = context.getSharedPreferences("apex_ai_session", Context.MODE_PRIVATE)

    init {
        AuthTokenProvider.update(prefs.getString(KEY_TOKEN, null))
    }

    fun saveSession(token: String, name: String, email: String) {
        AuthTokenProvider.update(token)
        prefs.edit()
            .putString(KEY_TOKEN, token)
            .putString(KEY_NAME, name)
            .putString(KEY_EMAIL, email)
            .apply()
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)
    fun getName(): String = prefs.getString(KEY_NAME, "Trader") ?: "Trader"
    fun getEmail(): String = prefs.getString(KEY_EMAIL, "") ?: ""
    fun isLocalDemoSession(): Boolean = getToken()?.startsWith(LOCAL_DEMO_PREFIX) == true

    fun clearSession() {
        AuthTokenProvider.update(null)
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_TOKEN = "token"
        private const val KEY_NAME = "name"
        private const val KEY_EMAIL = "email"
        const val LOCAL_DEMO_PREFIX = "LOCAL_DEMO_"
    }
}
