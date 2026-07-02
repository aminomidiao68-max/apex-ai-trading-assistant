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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.data.model.CandleDto
import java.util.Locale
import kotlin.math.max

@Composable
fun ChartScreen(viewModel: ChartViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val last = state.candles.lastOrNull()
    val snapshot = state.latestSnapshot
    val visibleCandles = viewModel.visibleCandles()
    val selectedCandle = viewModel.selectedVisibleCandle()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Live Chart", style = MaterialTheme.typography.headlineSmall)
            Text("${state.symbol} • ${state.timeframe}")
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("BTCUSDT", "crypto") }) { Text("BTC") }
                        Button(onClick = { viewModel.selectAsset("ETHUSDT", "crypto") }) { Text("ETH") }
                        Button(onClick = { viewModel.selectAsset("EURUSD", "forex") }) { Text("EURUSD") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.selectAsset("XAUUSD", "forex") }) { Text("XAUUSD") }
                        Button(onClick = { viewModel.selectTimeframe("15m") }) { Text("15m") }
                        Button(onClick = { viewModel.selectTimeframe("1h") }) { Text("1h") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.loadChart() }) { Text(if (state.loading) "Loading..." else "Reload") }
                        Button(onClick = { viewModel.reconnectStream() }) { Text("Reconnect") }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { viewModel.zoomIn() }) { Text("Zoom +") }
                        Button(onClick = { viewModel.zoomOut() }) { Text("Zoom -") }
                        Button(onClick = { viewModel.panLeft() }) { Text("←") }
                        Button(onClick = { viewModel.panRight() }) { Text("→") }
                    }
                    state.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
                    snapshot?.let {
                        Text(
                            "Live Price: ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}% • ${it.status}",
                            color = when {
                                (it.change_pct ?: 0.0) > 0 -> Color(0xFF2ECC71)
                                (it.change_pct ?: 0.0) < 0 -> Color(0xFFE74C3C)
                                else -> MaterialTheme.colorScheme.onSurface
                            }
                        )
                        it.error?.let { message ->
                            Text("Stream Error: $message", color = MaterialTheme.colorScheme.error)
                        }
                    }
                    Text("Stream Status: ${state.streamStatus} • Visible candles: ${visibleCandles.size}")
                    Text("Gesture: pinch to zoom, drag horizontally to pan, tap candle for crosshair")
                    last?.let {
                        Text("Last Candle • O: ${it.open}  H: ${it.high}  L: ${it.low}  C: ${it.close}")
                    }
                    selectedCandle?.let {
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text("Selected Candle", style = MaterialTheme.typography.titleMedium)
                                Text("Time: ${it.timestamp}")
                                Text("O: ${it.open} • H: ${it.high} • L: ${it.low} • C: ${it.close}")
                                Text("Volume: ${it.volume}")
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
    Card(modifier = Modifier.fillMaxWidth()) {
        if (candles.isEmpty()) {
            Text("No chart data available", modifier = Modifier.padding(16.dp))
            return@Card
        }

        var chartWidthPx by remember { mutableIntStateOf(0) }
        val minPrice = candles.minOf { it.low }
        val maxPrice = candles.maxOf { it.high }
        val range = max(maxPrice - minPrice, 0.0000001)
        val selected = selectedIndex.coerceIn(0, candles.size - 1)
        val selectedCandle = candles[selected]

        Column(modifier = Modifier.padding(12.dp)) {
            Text("Candlestick View")
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
                            text = "Live ${String.format(Locale.US, "%.4f", it)}",
                            color = Color(0xFF4DD0E1)
                        )
                    }
                    Text(
                        text = "Crosshair ${String.format(Locale.US, "%.4f", selectedCandle.close)}",
                        color = Color(0xFFFFC107)
                    )
                }
            }
            Text("Low: ${String.format(Locale.US, "%.4f", minPrice)}")
            Text("High: ${String.format(Locale.US, "%.4f", maxPrice)}")
        }
    }
}
