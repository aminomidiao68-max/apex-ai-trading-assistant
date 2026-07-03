package com.arena.smartmoney.ui.readiness

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun ReadinessScreen(viewModel: ReadinessViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val readiness = state.readiness
    val t = rememberTranslator()

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(
                t("System Readiness", "آمادگی سیستم"),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                t(
                    "Production readiness, blockers and warnings before real activation.",
                    "آمادگی نسخه عملیاتی، موانع و هشدارها پیش از فعال‌سازی واقعی."
                )
            )
        }
        item {
            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp)) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
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
                            style = MaterialTheme.typography.titleLarge
                        )
                        Text(
                            t("Ready / Warning / Missing", "آماده / هشدار / کمبود") +
                                ": ${it.ready_count} / ${it.warning_count} / ${it.missing_count}"
                        )
                        Text(
                            when (it.overall_status) {
                                "ready" -> t("System can move toward production with final checks.", "سیستم با انجام بررسی‌های نهایی می‌تواند به سمت نسخه عملیاتی حرکت کند.")
                                "partial" -> t("Some modules are usable, but several items still need completion.", "بعضی ماژول‌ها قابل استفاده‌اند، اما چند مورد هنوز باید تکمیل شوند.")
                                else -> t("Critical items are blocking full live readiness right now.", "در حال حاضر موارد مهمی جلوی آمادگی کامل برای استفاده زنده را گرفته‌اند.")
                            }
                        )
                    }
                }
            }
        }
        readiness?.let { data ->
            items(data.items.size) { index ->
                val item = data.items[index]
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text(item.key, style = MaterialTheme.typography.titleMedium)
                        Text(t("Category", "دسته‌بندی") + ": ${item.category}")
                        Text(
                            t("Status", "وضعیت") + ": ${localizedStatus(t, item.status)}",
                            color = statusColor(item.status)
                        )
                        Text(item.message)
                    }
                }
            }
        }
    }
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
        "ready" -> Color(0xFF2ECC71)
        "partial", "warning" -> Color(0xFFFFC857)
        else -> Color(0xFFE85B5B)
    }
}
