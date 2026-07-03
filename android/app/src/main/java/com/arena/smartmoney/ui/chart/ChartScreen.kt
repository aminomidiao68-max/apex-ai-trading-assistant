package com.arena.smartmoney.ui.chart

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.data.model.CandleDto
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.util.Locale
import kotlin.math.max

@Composable
fun ChartScreen(viewModel: ChartViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val last = state.candles.lastOrNull()
    val snapshot = state.latestSnapshot
    val visibleCandles = viewModel.visibleCandles()
    val selectedCandle = viewModel.selectedVisibleCandle()
    val t = rememberTranslator()
    val restFallbackMode = state.streamStatus.contains("404") || state.streamStatus.contains("error", ignoreCase = true)

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                t("Live Chart", "نمودار زنده"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text("${state.symbol} • ${state.timeframe}")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("BTCUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("BTC") }
                        Button(onClick = { viewModel.selectAsset("ETHUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("ETH") }
                        Button(onClick = { viewModel.selectAsset("EURUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("EURUSD") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("XAUUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("XAUUSD") }
                        Button(onClick = { viewModel.selectTimeframe("15m") }, modifier = Modifier.weight(1f)) { Text("15m") }
                        Button(onClick = { viewModel.selectTimeframe("1h") }, modifier = Modifier.weight(1f)) { Text("1h") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.loadChart() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Loading...", "در حال بارگذاری...") else t("Reload", "بارگذاری مجدد"))
                        }
                        Button(onClick = { viewModel.reconnectStream() }, modifier = Modifier.weight(1f)) {
                            Text(t("Reconnect", "اتصال مجدد"))
                        }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.zoomIn() }, modifier = Modifier.weight(1f)) { Text(t("Zoom +", "بزرگنمایی +")) }
                        Button(onClick = { viewModel.zoomOut() }, modifier = Modifier.weight(1f)) { Text(t("Zoom -", "بزرگنمایی -")) }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.panLeft() }, modifier = Modifier.weight(1f)) { Text(t("Left", "چپ")) }
                        Button(onClick = { viewModel.panRight() }, modifier = Modifier.weight(1f)) { Text(t("Right", "راست")) }
                    }
                    state.error?.let {
                        Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error)
                    }
                    snapshot?.let {
                        Text(
                            t("Live Price", "قیمت لحظه‌ای") + ": ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}% • ${it.status}",
                            color = when {
                                (it.change_pct ?: 0.0) > 0 -> Color(0xFF2ECC71)
                                (it.change_pct ?: 0.0) < 0 -> Color(0xFFE74C3C)
                                else -> MaterialTheme.colorScheme.onSurface
                            }
                        )
                    }
                    Text(
                        if (restFallbackMode) {
                            t(
                                "Realtime websocket is unavailable right now, but REST candle data is active and the chart remains usable.",
                                "در حال حاضر وب‌سوکت لحظه‌ای در دسترس نیست، اما داده کندل از REST فعال است و نمودار همچنان قابل استفاده است."
                            )
                        } else {
                            t(
                                "Realtime stream is connected and updating the chart.",
                                "استریم لحظه‌ای متصل است و نمودار را بروزرسانی می‌کند."
                            )
                        },
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        t("Visible candles", "کندل‌های قابل مشاهده") +
                            ": ${visibleCandles.size} • ${t("Status", "وضعیت")}: ${state.streamStatus}"
                    )
                    Text(
                        t(
                            "Gesture: pinch to zoom, drag horizontally to pan, tap a candle for the crosshair.",
                            "حرکت‌ها: با دو انگشت زوم کن، افقی بکش تا جابه‌جا شوی و روی کندل بزن تا کراس‌هِر فعال شود."
                        )
                    )
                    last?.let {
                        Text(
                            t("Last Candle", "آخرین کندل") +
                                " • O: ${it.open}  H: ${it.high}  L: ${it.low}  C: ${it.close}"
                        )
                    }
                    selectedCandle?.let {
                        Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
                            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(t("Selected Candle", "کندل انتخاب‌شده"), style = MaterialTheme.typography.titleMedium)
                                Text(t("Time", "زمان") + ": ${it.timestamp}")
                                Text("O: ${it.open} • H: ${it.high} • L: ${it.low} • C: ${it.close}")
                                Text(t("Volume", "حجم") + ": ${it.volume}")
                            }
                        }
                    }
                    CandlestickChart(
                        candles = visibleCandles,
                        selectedIndex = state.selectedVisibleIndex,
                        livePrice = snapshot?.last_price,
                        onGesture = viewModel::applyGesture,
                        onTap = viewModel::selectVisibleCandleFromTap
                    )
                }
            }
        }
    }
}

@Composable
private fun CandlestickChart(
    candles: List<CandleDto>,
    selectedIndex: Int,
    livePrice: Double?,
    onGesture: (Float, Float) -> Unit,
    onTap: (Float, Float) -> Unit
) {
    val t = rememberTranslator()

    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
        if (candles.isEmpty()) {
            Text(t("No chart data available", "داده‌ای برای نمودار موجود نیست"), modifier = Modifier.padding(16.dp))
        } else {
            var chartWidthPx by remember { mutableIntStateOf(0) }
            val minPrice = candles.minOf { it.low }
            val maxPrice = candles.maxOf { it.high }
            val range = max(maxPrice - minPrice, 0.0000001)
            val selected = selectedIndex.coerceIn(0, candles.size - 1)
            val selectedCandle = candles[selected]

            Column(modifier = Modifier.padding(12.dp)) {
                Text(t("Candlestick View", "نمای کندلی"), style = MaterialTheme.typography.titleMedium)
                Box(modifier = Modifier.fillMaxWidth()) {
                    Canvas(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(300.dp)
                            .padding(top = 12.dp)
                            .onSizeChanged { chartWidthPx = it.width }
                            .pointerInput(candles.size) {
                                detectTapGestures { offset ->
                                    onTap(offset.x, chartWidthPx.toFloat())
                                }
                            }
                            .pointerInput(candles.size) {
                                detectTransformGestures { _, pan, zoom, _ ->
                                    onGesture(pan.x, zoom)
                                }
                            }
                    ) {
                        val candleCount = candles.size
                        val slotWidth = size.width / candleCount
                        val bodyWidth = slotWidth * 0.55f

                        repeat(5) { step ->
                            val y = size.height * step / 4f
                            drawLine(
                                color = Color(0xFF26334C),
                                start = Offset(0f, y),
                                end = Offset(size.width, y),
                                strokeWidth = 1f
                            )
                        }

                        candles.forEachIndexed { index, candle ->
                            val centerX = slotWidth * index + slotWidth / 2f
                            val highY = size.height - (((candle.high - minPrice) / range).toFloat() * size.height)
                            val lowY = size.height - (((candle.low - minPrice) / range).toFloat() * size.height)
                            val openY = size.height - (((candle.open - minPrice) / range).toFloat() * size.height)
                            val closeY = size.height - (((candle.close - minPrice) / range).toFloat() * size.height)
                            val bullish = candle.close >= candle.open
                            val color = if (bullish) Color(0xFF2ECC71) else Color(0xFFE74C3C)

                            drawLine(
                                color = color,
                                start = Offset(centerX, highY),
                                end = Offset(centerX, lowY),
                                strokeWidth = 2f
                            )

                            val top = minOf(openY, closeY)
                            val bottom = maxOf(openY, closeY)
                            drawRoundRect(
                                color = color,
                                topLeft = Offset(centerX - bodyWidth / 2f, top),
                                size = Size(bodyWidth, max(bottom - top, 4f)),
                                cornerRadius = CornerRadius(4f, 4f)
                            )
                        }

                        val selectedX = slotWidth * selected + slotWidth / 2f
                        val selectedCloseY = size.height - (((selectedCandle.close - minPrice) / range).toFloat() * size.height)
                        drawLine(
                            color = Color(0xFFFFC107),
                            start = Offset(selectedX, 0f),
                            end = Offset(selectedX, size.height),
                            strokeWidth = 2f
                        )
                        drawLine(
                            color = Color(0xFFFFC107),
                            start = Offset(0f, selectedCloseY),
                            end = Offset(size.width, selectedCloseY),
                            strokeWidth = 2f
                        )
                        drawCircle(
                            color = Color(0xFFFFC107),
                            radius = 6f,
                            center = Offset(selectedX, selectedCloseY)
                        )

                        livePrice?.let { price ->
                            val priceY = size.height - (((price - minPrice) / range).toFloat() * size.height)
                            if (priceY in 0f..size.height) {
                                drawLine(
                                    color = Color(0xFF4DD0E1),
                                    start = Offset(0f, priceY),
                                    end = Offset(size.width, priceY),
                                    strokeWidth = 2f
                                )
                            }
                        }
                    }
                    Column(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(8.dp),
                        horizontalAlignment = Alignment.End
                    ) {
                        livePrice?.let {
                            Text(
                                text = t("Live", "زنده") + " ${String.format(Locale.US, "%.4f", it)}",
                                color = Color(0xFF4DD0E1)
                            )
                        }
                        Text(
                            text = t("Crosshair", "کراس‌هِر") + " ${String.format(Locale.US, "%.4f", selectedCandle.close)}",
                            color = Color(0xFFFFC107)
                        )
                    }
                }
                Text(t("Low", "کمینه") + ": ${String.format(Locale.US, "%.4f", minPrice)}")
                Text(t("High", "بیشینه") + ": ${String.format(Locale.US, "%.4f", maxPrice)}")
            }
        }
    }
}
