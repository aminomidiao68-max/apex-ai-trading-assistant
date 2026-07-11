@file:OptIn(ExperimentalMaterial3Api::class)
package com.arena.smartmoney.ui.chart

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.model.SmcZone
import com.arena.smartmoney.data.repository.TradingRepository
import kotlinx.coroutines.launch

private val BgDark = Color(0xFF0A0E17)
private val Surf = Color(0xFF121724)
private val Surf2 = Color(0xFF1A2030)
private val Gold = Color(0xFFD4AF37)
private val GoldDim = Color(0xFF8C7630)
private val TH = Color(0xFFF5F0DC)
private val TL = Color(0xFF9A9380)
private val UpC = Color(0xFF3DDC97)
private val DnC = Color(0xFFFF5A5F)
private val FvgC = Color(0xFFB388FF)
private val BrkC = Color(0xFFFF9F43)
private val LiqC = Color(0xFF54A0FF)

@Composable
fun ChartScreen(onBack: (() -> Unit)? = null) {
    val repo = remember { TradingRepository() }
    val scope = rememberCoroutineScope()
    var r by remember { mutableStateOf(SmcReport()) }
    var loading by remember { mutableStateOf(true) }
    var sym by remember { mutableStateOf("XAUUSD") }
    var mkt by remember { mutableStateOf("forex") }
    var tf by remember { mutableStateOf("15min") }
    fun load() {
        scope.launch {
            loading = true
            try { r = repo.getSmcAnalysis(sym, mkt, tf, 220) } finally { loading = false }
        }
    }
    LaunchedEffect(sym, mkt, tf) { load() }
    Scaffold(
        containerColor = BgDark,
        topBar = {
            TopAppBar(
                title = { Text("SMC Chart", color = Gold, fontWeight = FontWeight.Bold, fontSize = 20.sp) },
                navigationIcon = {
                    if (onBack != null) IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "back", tint = Gold)
                    }
                },
                actions = { IconButton(onClick = { load() }) { Icon(Icons.Default.Refresh, "r", tint = Gold) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BgDark)
            )
        }
    ) { pad ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(pad).padding(horizontal = 14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Card(colors = CardDefaults.cardColors(containerColor = Surf), shape = RoundedCornerShape(14.dp)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()) {
                            Column {
                                Text(r.symbol.ifBlank { sym }, color = TH, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                                Text(r.timeframe.ifBlank { tf }, color = TL, fontSize = 12.sp)
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                val p = r.price
                                Text(if (p > 0f) "%.4f".format(p) else "-", color = Gold, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                                val bc = when (r.bias) { "bullish" -> UpC; "bearish" -> DnC; else -> GoldDim }
                                val bl = when (r.bias) { "bullish" -> "BULLISH"; "bearish" -> "BEARISH"; else -> "NEUTRAL" }
                                Text(bl, color = bc, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                        Spacer(Modifier.height(10.dp))
                        Text(if (loading) "Loading..." else r.note.ifBlank { "No data." }, color = TH, fontSize = 13.sp)
                        Spacer(Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Chip("conf ${r.confluence}", if (r.confluence >= 2) Gold else GoldDim)
                            Chip("${r.candlesCount}c", TL)
                            Chip(r.status.ifBlank { "-" }, TL)
                        }
                    }
                }
            }
            item {
                Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(14.dp)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Trade Levels", color = Gold, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Lvl("Entry", r.levels.entry, Gold)
                            Lvl("SL", r.levels.sl, DnC)
                            Lvl("TP", r.levels.tp, UpC)
                        }
                    }
                }
            }
            if (r.orderBlocks.isNotEmpty()) item { ST("Order Blocks", Gold) }
            items(r.orderBlocks.take(8)) { Zc(it, "OB", if (it.side == "bullish") UpC else DnC) }
            if (r.fvg.isNotEmpty()) item { ST("Fair Value Gaps", FvgC) }
            items(r.fvg.take(8)) { Zc(it, "FVG", FvgC) }
            if (r.breakers.isNotEmpty()) item { ST("Breaker Blocks", BrkC) }
            items(r.breakers.take(5)) { Zc(it, "BRK", BrkC) }
            if (r.inducements.isNotEmpty()) item { ST("Liquidity Sweeps", LiqC) }
            items(r.inducements.take(10)) { lbl ->
                Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(10.dp)) {
                    Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(lbl.kind.replace("_", " "), color = LiqC, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        Text("%.4f idx %d".format(lbl.price, lbl.index), color = TH, fontSize = 12.sp)
                    }
                }
            }
            if (r.events.isNotEmpty()) item { ST("BOS / CHoCH Events", Gold) }
            items(r.events.takeLast(8)) { ev ->
                Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(10.dp)) {
                    Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        val c = if (ev.dir == "bullish") UpC else DnC
                        Text(ev.kind + " · " + ev.dir, color = c, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        Text("%.4f".format(ev.price), color = TH, fontSize = 12.sp)
                    }
                }
            }
            item { Spacer(Modifier.height(50.dp)) }
            item { Text("Created by Amin Omidi", color = GoldDim, fontSize = 11.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center) }
        }
    }
}

@Composable
private fun ST(t: String, c: Color) {
    Text(t, color = c, fontSize = 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp))
}
@Composable
private fun Chip(t: String, c: Color) {
    Surface(color = c.copy(alpha = 0.15f), shape = RoundedCornerShape(999.dp)) {
        Text(t, color = c, fontSize = 11.sp, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), fontWeight = FontWeight.SemiBold)
    }
}
@Composable
private fun RowScope.Lvl(label: String, v: Float?, c: Color) {
    Card(colors = CardDefaults.cardColors(containerColor = BgDark), shape = RoundedCornerShape(10.dp), modifier = Modifier.weight(1f)) {
        Column(Modifier.padding(10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(label, color = TL, fontSize = 11.sp)
            Spacer(Modifier.height(4.dp))
            Text(if (v != null && v > 0f) "%.4f".format(v) else "-", color = c, fontSize = 14.sp, fontWeight = FontWeight.Bold)
        }
    }
}
@Composable
private fun Zc(z: SmcZone, tag: String, c: Color) {
    Card(colors = CardDefaults.cardColors(containerColor = Surf2), shape = RoundedCornerShape(10.dp)) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text("$tag · ${z.side}", color = c, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                Text("idx ${z.index}", color = TL, fontSize = 10.sp)
            }
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("top: %.4f".format(z.top), color = UpC, fontSize = 12.sp)
                Text("bot: %.4f".format(z.bottom), color = DnC, fontSize = 12.sp)
            }
        }
    }
}
