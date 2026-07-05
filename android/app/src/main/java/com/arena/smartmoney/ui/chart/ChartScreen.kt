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
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.formatDisplayTimestamp
import com.arena.smartmoney.ui.i18n.localizeBackendStatus
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

    PremiumScreenBackground {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("Live Chart", "نمودار زنده"),
                    subtitle = "${state.symbol} • ${state.timeframe}"
                )
            }
            item {
                PremiumGlassCard {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("BTCUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("BTC") }
                        Button(onClick = { viewModel.selectAsset("ETHUSDT", "crypto") }, modifier = Modifier.weight(1f)) { Text("ETH") }
                        OutlinedButton(onClick = { viewModel.selectAsset("EURUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("EURUSD") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { viewModel.selectAsset("XAUUSD", "forex") }, modifier = Modifier.weight(1f)) { Text("XAUUSD") }
                        Button(onClick = { viewModel.selectTimeframe("1m") }, modifier = Modifier.weight(1f)) { Text("1m") }
                        Button(onClick = { viewModel.selectTimeframe("15m") }, modifier = Modifier.weight(1f)) { Text("15m") }
                        OutlinedButton(onClick = { viewModel.selectTimeframe("1h") }, modifier = Modifier.weight(1f)) { Text("1h") }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.loadChart() }, modifier = Modifier.weight(1f)) {
                            Text(if (state.loading) t("Loading...", "در حال بارگذاری...") else t("Reload", "بارگذاری مجدد"))
                        }
                        OutlinedButton(onClick = { viewModel.reconnectStream() }, modifier = Modifier.weight(1f)) {
                            Text(t("Reconnect", "اتصال مجدد"))
                        }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { viewModel.zoomIn() }, modifier = Modifier.weight(1f)) { Text(t("Zoom +", "بزرگنمایی +")) }
                        OutlinedButton(onClick = { viewModel.zoomOut() }, modifier = Modifier.weight(1f)) { Text(t("Zoom -", "بزرگنمایی -")) }
                    }
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { viewModel.panLeft() }, modifier = Modifier.weight(1f)) { Text(t("Left", "چپ")) }
                        OutlinedButton(onClick = { viewModel.panRight() }, modifier = Modifier.weight(1f)) { Text(t("Right", "راست")) }
                    }
                    state.error?.let { Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error) }
                    snapshot?.let {
                        Text(
                            t("Live Price", "قیمت لحظه‌ای") + ": ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}% • ${localizeBackendStatus(it.status, t)}",
                            color = when {
                                (it.change_pct ?: 0.0) > 0 -> Color(0xFF33E6A6)
                                (it.change_pct ?: 0.0) < 0 -> Color(0xFFFF7A7A)
                                else -> Color.White
                            },
                            fontWeight = FontWeight.Bold
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
                        color = if (restFallbackMode) Color(0xFFFFD27A) else Color(0xFF67ECFF)
                    )
                    Text(t("Visible candles", "کندل‌های قابل مشاهده") + ": ${visibleCandles.size} • ${t("Status", "وضعیت")}: ${localizeBackendStatus(state.streamStatus, t)}", color = Color(0xFFBCEEFF))
                    Text(t("Gesture: pinch to zoom, drag horizontally to pan, tap a candle for the crosshair.", "حرکت‌ها: با دو انگشت زوم کن، افقی بکش تا جابه‌جا شوی و روی کندل بزن تا کراس‌هِر فعال شود."), color = Color(0xFFBCEEFF))
                    last?.let {
                        Text(t("Last Candle", "آخرین کندل") + " • O: ${it.open}  H: ${it.high}  L: ${it.low}  C: ${it.close}", color = Color.White)
                    }
                    selectedCandle?.let {
                        PremiumGlassCard(borderColor = Color(0x40FFC857)) {
                            Text(t("Selected Candle", "کندل انتخاب‌شده"), style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                            Text(t("Time", "زمان") + ": ${formatDisplayTimestamp(it.timestamp)}", color = Color.White)
                            Text("O: ${it.open} • H: ${it.high} • L: ${it.low} • C: ${it.close}", color = Color.White)
                            Text(t("Volume", "حجم") + ": ${it.volume}", color = Color(0xFFFFD27A))
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

    PremiumGlassCard {
        if (candles.isEmpty()) {
            Text(t("No chart data available", "داده‌ای برای نمودار موجود نیست"), color = Color.White)
        } else {
            var chartWidthPx by remember { mutableIntStateOf(0) }
            val minPrice = candles.minOf { it.low }
            val maxPrice = candles.maxOf { it.high }
            val range = max(maxPrice - minPrice, 0.0000001)
            val selected = selectedIndex.coerceIn(0, candles.size - 1)
            val selectedCandle = candles[selected]

            Column {
                Text(t("Candlestick View", "نمای کندلی"), style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
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
                            val color = if (bullish) Color(0xFF33E6A6) else Color(0xFFFF7A7A)

                            drawLine(color = color, start = Offset(centerX, highY), end = Offset(centerX, lowY), strokeWidth = 2f)

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
                        drawLine(color = Color(0xFFFFC107), start = Offset(selectedX, 0f), end = Offset(selectedX, size.height), strokeWidth = 2f)
                        drawLine(color = Color(0xFFFFC107), start = Offset(0f, selectedCloseY), end = Offset(size.width, selectedCloseY), strokeWidth = 2f)
                        drawCircle(color = Color(0xFFFFC107), radius = 6f, center = Offset(selectedX, selectedCloseY))

                        livePrice?.let { price ->
                            val priceY = size.height - (((price - minPrice) / range).toFloat() * size.height)
                            if (priceY in 0f..size.height) {
                                drawLine(color = Color(0xFF4DD0E1), start = Offset(0f, priceY), end = Offset(size.width, priceY), strokeWidth = 2f)
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
                            Text(text = t("Live", "زنده") + " ${String.format(Locale.US, "%.4f", it)}", color = Color(0xFF4DD0E1))
                        }
                        Text(text = t("Crosshair", "کراس‌هِر") + " ${String.format(Locale.US, "%.4f", selectedCandle.close)}", color = Color(0xFFFFC107))
                    }
                }
                Text(t("Low", "کمینه") + ": ${String.format(Locale.US, "%.4f", minPrice)}", color = Color(0xFFBCEEFF))
                Text(t("High", "بیشینه") + ": ${String.format(Locale.US, "%.4f", maxPrice)}", color = Color(0xFFBCEEFF))
            }
        }
    }
}
