package com.arena.smartmoney.data.network

/**
 * In-memory access-token bridge used by the OkHttp interceptor.
 *
 * Persistence remains in SessionManager. Local demo tokens are intentionally
 * never sent to the backend because they are not server-issued credentials.
 */
object AuthTokenProvider {
    @Volatile
    private var token: String? = null

    fun update(value: String?) {
        token = value?.takeIf { it.isNotBlank() && !it.startsWith("LOCAL_DEMO_") }
    }

    fun authorizationHeader(): String? = token?.let { "Bearer $it" }
}
