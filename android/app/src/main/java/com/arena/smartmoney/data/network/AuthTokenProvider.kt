package com.arena.smartmoney.data.network

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

/**
 * In-memory access-token bridge used by the OkHttp interceptor.
 *
 * Persistence remains in SessionManager. Local demo tokens are intentionally
 * never sent to the backend because they are not server-issued credentials.
 */
object AuthTokenProvider {
    @Volatile
    private var token: String? = null
    private val _unauthorizedEvents = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val unauthorizedEvents = _unauthorizedEvents.asSharedFlow()

    fun update(value: String?) {
        token = value?.takeIf { it.isNotBlank() && !it.startsWith("LOCAL_DEMO_") }
    }

    fun authorizationHeader(): String? = token?.let { "Bearer $it" }

    fun hasServerToken(): Boolean = token != null

    fun clear() {
        token = null
    }

    fun notifyUnauthorized() {
        token = null
        _unauthorizedEvents.tryEmit(Unit)
    }
}
