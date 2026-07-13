package com.arena.smartmoney.data.network

import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException

/** Retries idempotent reads during Render cold starts and transient routing failures. */
class NetworkRetryInterceptor(
    private val maxRetries: Int = 3,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val retryableMethod = request.method == "GET" || request.method == "HEAD"
        if (!retryableMethod) return chain.proceed(request)

        var lastException: IOException? = null
        for (attempt in 0..maxRetries) {
            try {
                val response = chain.proceed(request)
                val retryableCode = response.code in listOf(429, 502, 503, 504)
                if (!retryableCode || attempt == maxRetries) return response
                val retryAfterMs = response.header("Retry-After")
                    ?.toLongOrNull()
                    ?.coerceIn(1L, 5L)
                    ?.times(1000L)
                response.close()
                Thread.sleep(retryAfterMs ?: backoff(attempt))
            } catch (error: IOException) {
                lastException = error
                if (attempt == maxRetries) throw error
                Thread.sleep(backoff(attempt))
            }
        }
        throw lastException ?: IOException("Network request failed after retries")
    }

    private fun backoff(attempt: Int): Long = when (attempt) {
        0 -> 600L
        1 -> 1_200L
        else -> 2_400L
    }
}
