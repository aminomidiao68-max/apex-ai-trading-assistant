package com.arena.smartmoney.ui.readiness

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.data.model.ShadowTimelineItemDto
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun ReadinessScreen(viewModel: ReadinessViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val readiness = state.readiness
    val t = rememberTranslator()

    PremiumScreenBackground {
        androidx.compose.foundation.lazy.LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                PremiumSectionHeader(
                    title = t("System Readiness", "آمادگی سیستم"),
                    subtitle = t(
                        "Production readiness, blockers and warnings before real activation.",
                        "آمادگی نسخه عملیاتی، موانع و هشدارها پیش از فعال‌سازی واقعی."
                    )
                )
            }
            item {
                PremiumGlassCard(borderColor = Color(0x40FFC857)) {
                    Button(onClick = { viewModel.load() }, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.loading) t("Refreshing...", "در حال بروزرسانی...") else t("Refresh Readiness", "بروزرسانی آمادگی"))
                    }
                    state.error?.let {
                        Text(t("Error", "خطا") + ": $it", color = MaterialTheme.colorScheme.error)
                    }
                    readiness?.let {
                        Text(
                            t("Overall Status", "وضعیت کلی") + ": ${localizedStatus(t, it.overall_status)}",
                            color = statusColor(it.overall_status),
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            t("Ready / Warning / Missing", "آماده / هشدار / کمبود") +
                                ": ${it.ready_count} / ${it.warning_count} / ${it.missing_count}",
                            color = Color.White
                        )
                        Text(
                            when (it.overall_status) {
                                "ready" -> t("System can move toward production with final checks.", "سیستم با انجام بررسی‌های نهایی می‌تواند به سمت نسخه عملیاتی حرکت کند.")
                                "partial" -> t("Some modules are usable, but several items still need completion.", "بعضی ماژول‌ها قابل استفاده‌اند، اما چند مورد هنوز باید تکمیل شوند.")
                                else -> t("Critical items are blocking full live readiness right now.", "در حال حاضر موارد مهمی جلوی آمادگی کامل برای استفاده زنده را گرفته‌اند.")
                            },
                            color = Color(0xFFDDF8FF)
                        )
                    }
                }
            }
            item {
                ForwardTestCard(
                    panel = state.panel,
                    timeline = state.timeline,
                    timelineExpanded = state.timelineExpanded,
                    timelineLoading = state.timelineLoading,
                    timelineError = state.timelineError,
                    onToggleTimeline = { viewModel.toggleTimeline() },
                    onRefreshTimeline = { viewModel.refreshTimeline() }
                )
            }
            readiness?.let { data ->
                items(data.items) { item ->
                    PremiumGlassCard(borderColor = statusColor(item.status).copy(alpha = 0.35f)) {
                        Text(item.key, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                        Text(t("Category", "دسته‌بندی") + ": ${item.category}", color = Color(0xFFDDF8FF))
                        Text(
                            t("Status", "وضعیت") + ": ${localizedStatus(t, item.status)}",
                            color = statusColor(item.status),
                            fontWeight = FontWeight.Bold
                        )
                        Text(item.message, color = Color.White)
                    }
                }
            }
        }
    }
}

@Composable
private fun ForwardTestCard(
    panel: com.arena.smartmoney.data.model.ShadowPanelDto?,
    timeline: com.arena.smartmoney.data.model.ShadowTimelineDto?,
    timelineExpanded: Boolean,
    timelineLoading: Boolean,
    timelineError: String?,
    onToggleTimeline: () -> Unit,
    onRefreshTimeline: () -> Unit
) {
    var filter by remember { mutableStateOf("ALL") } // ALL, CANDIDATE, RESOLVED, WINLOSS
    PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
        Text(
            "🧪 آزمون رو‌به‌جلو (سایهٔ زنده)",
            style = MaterialTheme.typography.titleLarge,
            color = Color.White,
            fontWeight = FontWeight.Bold
        )
        Text(
            "منبع: سرور سایه با دیتابیس ماندگار (PostgreSQL) — همان موتور، دادهٔ واقعی بازار",
            color = Color(0x99FFFFFF),
            fontSize = MaterialTheme.typography.bodySmall.fontSize
        )
        if (panel == null) {
            Text(
                "پنل سایه در دسترس نیست (سرور استیجینگ خواب است — ۳۰ تا ۶۰ ثانیه دیگر دوباره بروزرسانی کنید).",
                color = Color(0xFFFFC857)
            )
            return@PremiumGlassCard
        }
        Text(
            "موتور فعلی: ${panel.currentEngineVersion ?: "?"} • مشاهده‌ها: ${panel.observationsCurrentEngine} • کاندیداهای اکشن: ${panel.candidatesCurrentEngine}",
            color = Color(0xFFDDF8FF)
        )
        Spacer(Modifier.height(10.dp))
        ProgressRow("معاملات حل‌شده (cohort فعلی)", panel.resolvedCurrentEngine, panel.minimumRequiredResolved)
        ProgressRow("حل‌شده‌های فعال‌شده", panel.activatedResolvedCurrentEngine, panel.minimumRequiredActivated)
        val span = panel.cohortSpanDays ?: 0.0
        ProgressRowDouble("طول دورهٔ کوهورت (روز)", span, 7.0)
        Spacer(Modifier.height(8.dp))
        if (panel.researchReadyCurrentEngine && panel.winRateCiLow != null && panel.winRateCiHigh != null) {
            val wl = panel.cohortWins + panel.cohortLosses
            Text(
                "نرخ برد کوهورت: ${panel.cohortWins} برد / ${panel.cohortLosses} باخت از $wl",
                color = Color(0xFF33E6A6),
                fontWeight = FontWeight.Bold
            )
            Text(
                "بازهٔ اطمینان ۹۵٪ (Wilson): ${(panel.winRateCiLow * 100).toInt()}٪ تا ${(panel.winRateCiHigh * 100).toInt()}٪",
                color = Color.White
            )
            Text(
                "این آمار توصیفیِ عملکرد سایه است، نه وعدهٔ آینده. precision_claimed=${panel.precisionClaimed}",
                color = Color(0xFFDDF8FF)
            )
        } else {
            Text(
                "دادهٔ کافی نیست (${panel.status}) — تا رسیدن به ۳۰ معاملهٔ حل‌شدهٔ فعال + ۷ روز، هیچ ادعای دقتی مطرح نمی‌شود.",
                color = Color(0xFFFFC857)
            )
        }
        Text(
            "سایه = بدون اجرای واقعی • actionable_for_live=${panel.actionableForLive} • اجرای زنده همچنان غیرفعال است.",
            color = Color(0x99FFFFFF),
            fontSize = MaterialTheme.typography.bodySmall.fontSize
        )
        Spacer(Modifier.height(12.dp))
        // Timeline toggle
        Button(
            onClick = onToggleTimeline,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1E3A5F))
        ) {
            Text(if (timelineExpanded) "▾ بستن تاریخچهٔ مشاهدات" else "▸ نمایش تاریخچهٔ کامل مشاهدات سایه (${timeline?.total ?: panel.observationsCurrentEngine} مشاهده)")
        }
        if (timelineExpanded) {
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                TimelineFilterChip("همه", filter == "ALL") { filter = "ALL" }
                TimelineFilterChip("کاندیدا", filter == "CANDIDATE") { filter = "CANDIDATE" }
                TimelineFilterChip("حل‌شده", filter == "RESOLVED") { filter = "RESOLVED" }
                TimelineFilterChip("برد/باخت", filter == "WINLOSS") { filter = "WINLOSS" }
            }
            Spacer(Modifier.height(6.dp))
            TextButton(onClick = onRefreshTimeline, modifier = Modifier.fillMaxWidth()) {
                Text(if (timelineLoading) "در حال بارگذاری..." else "⟳ بروزرسانی تاریخچه (۵۰ مورد اخیر)")
            }
            timelineError?.let {
                Text("خطا: $it", color = Color(0xFFFF7A7A), fontSize = MaterialTheme.typography.bodySmall.fontSize)
            }
            val items = timeline?.items ?: emptyList()
            if (!timelineLoading && items.isEmpty() && timeline != null) {
                Text(
                    "هنوز سابقه‌ای برای این موتور وجود ندارد — cohort از ${panel.currentEngineVersion} تازه شروع شده است.",
                    color = Color(0xFFFFC857)
                )
            }
            if (timelineLoading && items.isEmpty()) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = Color(0xFF33E6A6), trackColor = Color(0x22FFFFFF))
            }
            val filtered = when (filter) {
                "CANDIDATE" -> items.filter { it.fusionStatus == "ACTIONABLE_CANDIDATE" }
                "RESOLVED" -> items.filter { it.outcomeStatus in setOf("WIN","LOSS","EXPIRED_ACTIVE","EXPIRED_NO_ENTRY") }
                "WINLOSS" -> items.filter { it.outcomeStatus in setOf("WIN","LOSS") && it.activated }
                else -> items
            }
            if (timeline != null && filtered.isEmpty() && items.isNotEmpty()) {
                Text("فیلتر انتخابی نتیجه‌ای ندارد — «همه» را امتحان کنید.", color = Color(0x99FFFFFF), fontSize = MaterialTheme.typography.bodySmall.fontSize)
            }
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                filtered.forEach { obs ->
                    TimelineItemCard(obs)
                }
            }
            if (timeline != null) {
                Text(
                    "نمایش ${filtered.size} از ${items.size} (۵۰ مورد اخیر، کل ${timeline.total}) • موتور ${timeline.currentEngineVersion}",
                    color = Color(0x66FFFFFF),
                    fontSize = MaterialTheme.typography.bodySmall.fontSize
                )
                Text(
                    "هر ردیف = یک مشاهدهٔ سایه با دادهٔ واقعی بازار. WIN/LOSS فقط وقتی activated=true و قیمت آینده حد ضرر/سود را لمس کرده باشد.",
                    color = Color(0x66FFFFFF),
                    fontSize = MaterialTheme.typography.bodySmall.fontSize
                )
            }
        }
    }
}

@Composable
private fun TimelineFilterChip(label: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label, fontSize = MaterialTheme.typography.bodySmall.fontSize) },
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = Color(0xFF33E6A6),
            selectedLabelColor = Color.Black,
            containerColor = Color(0x22FFFFFF),
            labelColor = Color.White
        )
    )
}

@Composable
private fun TimelineItemCard(obs: ShadowTimelineItemDto) {
    val outcomeColor = when (obs.outcomeStatus) {
        "WIN" -> Color(0xFF33E6A6)
        "LOSS" -> Color(0xFFFF7A7A)
        "EXPIRED_ACTIVE" -> Color(0xFFB8B8FF)
        "EXPIRED_NO_ENTRY" -> Color(0xFF9AA0B0)
        "PENDING" -> Color(0xFFFFC857)
        else -> Color.White
    }
    val statusFa = when (obs.fusionStatus) {
        "ACTIONABLE_CANDIDATE" -> "کاندیدای اکشن"
        "WATCH" -> "تحت نظر"
        "NO_TRADE" -> "بدون معامله"
        else -> obs.fusionStatus
    }
    val outcomeFa = when (obs.outcomeStatus) {
        "WIN" -> "برد"
        "LOSS" -> "باخت"
        "EXPIRED_ACTIVE" -> "فعال→انقضا"
        "EXPIRED_NO_ENTRY" -> "عدم ورود"
        "PENDING" -> "در انتظار"
        else -> obs.outcomeStatus
    }
    // Persian short date: take ISO and show YYYY-MM-DD HH:mm
    val capturedShort = try { obs.capturedAt.take(16).replace("T"," ") } catch (_: Exception) { obs.capturedAt }
    val rrStr = obs.realizedRr?.let { "%.2f".format(it) } ?: "—"
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(2.dp),
    ) {
        // Outer card look via nested PremiumGlassCard would be too heavy; use simple Column with background via Text weight
        androidx.compose.foundation.layout.Box(
            modifier = Modifier
                .fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("${obs.symbol} • ${obs.market.ifEmpty { "crypto" }} • ${obs.side}", color = Color.White, fontWeight = FontWeight.Bold, fontSize = MaterialTheme.typography.bodyMedium.fontSize)
                    Text(outcomeFa, color = outcomeColor, fontWeight = FontWeight.Bold, fontSize = MaterialTheme.typography.bodyMedium.fontSize)
                }
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("$statusFa • ${obs.probability?.let { "$it٪" } ?: "—"}", color = Color(0xFFDDF8FF), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                    Text(capturedShort, color = Color(0x99FFFFFF), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                }
                if (obs.fusionStatus == "ACTIONABLE_CANDIDATE") {
                    Text(
                        "ورود ${obs.entryPrice?.let { "%.4f".format(it) } ?: "—"} • حدضرر ${obs.stopPrice?.let { "%.4f".format(it) } ?: "—"} • هدف ${obs.targetPrice?.let { "%.4f".format(it) } ?: "—"} • TF ${obs.resolutionTimeframe ?: "—"}",
                        color = Color(0xFFB0E0FF),
                        fontSize = MaterialTheme.typography.bodySmall.fontSize
                    )
                }
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("RR تحقق‌یافته: $rrStr • میله‌ها: ${obs.barsObserved}", color = if (obs.realizedRr != null && obs.realizedRr > 0) Color(0xFF33E6A6) else Color(0xFFDDF8FF), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                    obs.resolutionReason?.let {
                        Text(it, color = Color(0x99FFFFFF), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                    }
                }
                if (obs.outcomeStatus == "PENDING") {
                    Text("نتیجه هنوز باز است — با کندل‌های آینده حل می‌شود.", color = Color(0xFFFFC857), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                }
                // thin divider
                Spacer(Modifier.height(4.dp))
                androidx.compose.foundation.layout.Box(modifier = Modifier.fillMaxWidth().height(1.dp).padding(horizontal = 0.dp)) {
                    androidx.compose.foundation.layout.Box(modifier = Modifier.fillMaxWidth().height(1.dp)) {
                    }
                }
            }
        }
        // divider line using Text
        Text("─".repeat(36), color = Color(0x1AFFFFFF), fontSize = MaterialTheme.typography.bodySmall.fontSize, maxLines = 1)
    }
}

@Composable
private fun ProgressRow(label: String, value: Int, required: Int) {
    val frac = if (required > 0) (value.toFloat() / required.toFloat()).coerceIn(0f, 1f) else 0f
    Text("$label: $value / $required", color = Color.White)
    LinearProgressIndicator(
        progress = { frac },
        modifier = Modifier.fillMaxWidth(),
        color = Color(0xFF33E6A6),
        trackColor = Color(0x33FFFFFF),
    )
    Spacer(Modifier.height(6.dp))
}

@Composable
private fun ProgressRowDouble(label: String, value: Double, required: Double) {
    val frac = if (required > 0.0) (value / required).toFloat().coerceIn(0f, 1f) else 0f
    Text("$label: ${"%.1f".format(value)} / ${"%.0f".format(required)}", color = Color.White)
    LinearProgressIndicator(
        progress = { frac },
        modifier = Modifier.fillMaxWidth(),
        color = Color(0xFF33E6A6),
        trackColor = Color(0x33FFFFFF),
    )
    Spacer(Modifier.height(6.dp))
}

private fun localizedStatus(t: (String, String) -> String, status: String): String {
    return when (status.lowercase()) {
        "ready" -> t("Ready", "آماده")
        "warning" -> t("Warning", "هشدار")
        "partial" -> t("Partial", "نیمه‌آماده")
        "missing" -> t("Missing", "موجود نیست")
        "blocked" -> t("Blocked", "مسدود")
        else -> status
    }
}

private fun statusColor(status: String): Color {
    return when (status.lowercase()) {
        "ready" -> Color(0xFF33E6A6)
        "partial", "warning" -> Color(0xFFFFC857)
        else -> Color(0xFFFF7A7A)
    }
}
