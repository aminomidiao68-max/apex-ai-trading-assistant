package com.arena.smartmoney.data.network

import com.arena.smartmoney.data.model.MarketStreamSnapshotDto
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class MarketWebSocketClient(
    private val baseWsUrl: String = AppConfig.marketWsUrl
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null

    fun connect(
        symbol: String,
        market: String,
        onStatus: (String) -> Unit,
        onSnapshot: (MarketStreamSnapshotDto) -> Unit
    ) {
        disconnect()
        onStatus("connecting")

        val request = Request.Builder()
            .url("$baseWsUrl?symbol=$symbol&market=$market")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                onStatus("connected")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val json = JSONObject(text)
                val snapshot = MarketStreamSnapshotDto(
                    symbol = json.optString("symbol", symbol),
                    market = json.optString("market", market),
                    last_price = json.optDoubleOrNull("last_price"),
                    change_pct = json.optDoubleOrNull("change_pct"),
                    source = json.optString("source", "websocket"),
                    status = json.optString("status", "streaming"),
                    error = json.optStringOrNull("error")
                )
                onSnapshot(snapshot)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                onStatus("error: ${t.message ?: "unknown"}")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                onStatus("closed")
            }
        })
    }

    fun disconnect() {
        webSocket?.close(1000, "disconnect")
        webSocket = null
    }
}

private fun JSONObject.optDoubleOrNull(key: String): Double? {
    return if (has(key) && !isNull(key)) optDouble(key) else null
}

private fun JSONObject.optStringOrNull(key: String): String? {
    return if (has(key) && !isNull(key)) optString(key) else null
}
