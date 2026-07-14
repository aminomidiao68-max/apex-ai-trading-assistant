package com.arena.smartmoney.ui.risk

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.components.premiumTextFieldColors
import com.arena.smartmoney.ui.components.premiumTextFieldStyle
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.util.Locale
import kotlin.math.abs

@Composable
fun RiskCalculatorScreen(viewModel: RiskCalculatorViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    val entryValue = state.entry.toDoubleOrNull() ?: 0.0
    val stopValue = state.stop.toDoubleOrNull() ?: 0.0
    val balanceValue = state.balance.toDoubleOrNull() ?: 0.0
    val riskPctValue = state.riskPct.toDoubleOrNull() ?: 0.0
    val stopDistance = abs(entryValue - stopValue)
    val plannedRiskCash = balanceValue * (riskPctValue / 100.0)
    val commandLabel = when {
        riskPctValue <= 0.5 -> t("Defensive", "دفاعی")
        riskPctValue <= 1.5 -> t("Balanced", "متعادل")
        riskPctValue <= 2.5 -> t("Aggressive", "تهاجمی")
        else -> t("High Risk", "پرریسک")
    }

    PremiumScreenBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            PremiumSectionHeader(
                title = t("Risk Command Center", "مرکز فرمان ریسک"),
                subtitle = t(
                    "Professional position sizing, capital defense and breakeven planning.",
                    "محاسبه حرفه‌ای حجم، دفاع از سرمایه و برنامه‌ریزی بریک‌اون."
                )
            )

            PremiumGlassCard {
                Text(t("Risk Snapshot", "نمای ریسک"), style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.Bold)
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    RiskChip(t("Profile", "پروفایل"), commandLabel, Modifier.weight(1f))
                    RiskChip(t("Stop Distance", "فاصله استاپ"), if (stopDistance > 0) String.format(Locale.US, "%.4f", stopDistance) else "-", Modifier.weight(1f))
                    RiskChip(t("Risk Cash", "ریسک نقدی"), if (plannedRiskCash > 0) String.format(Locale.US, "%.2f", plannedRiskCash) else "-", Modifier.weight(1f))
                }
                Text(
                    when {
                        riskPctValue > 2.0 -> t("Risk is elevated. Consider scaling down before executing live.", "ریسک بالا است. قبل از اجرای زنده بهتر است حجم را کمتر کنی.")
                        stopDistance == 0.0 -> t("Define entry and stop properly so the engine can size the position accurately.", "ورود و استاپ را درست وارد کن تا موتور بتواند حجم را دقیق محاسبه کند.")
                        else -> t("Use this board to pressure-test each trade before sending it to execution.", "از این برد استفاده کن تا هر معامله را قبل از ارسال به اجرا تحت فشار بررسی کنی.")
                    },
                    color = Color(0xFFDDF8FF)
                )
            }

            PremiumGlassCard {
                OutlinedTextField(
                    value = state.entry,
                    onValueChange = viewModel::onEntryChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Entry Price", "قیمت ورود")) },
                    shape = RoundedCornerShape(18.dp),
                    singleLine = true,
                    textStyle = premiumTextFieldStyle(),
                    colors = premiumTextFieldColors()
                )
                OutlinedTextField(
                    value = state.stop,
                    onValueChange = viewModel::onStopChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Stop Loss", "حد ضرر")) },
                    shape = RoundedCornerShape(18.dp),
                    singleLine = true,
                    textStyle = premiumTextFieldStyle(),
                    colors = premiumTextFieldColors()
                )
                OutlinedTextField(
                    value = state.balance,
                    onValueChange = viewModel::onBalanceChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Account Balance", "بالانس حساب")) },
                    shape = RoundedCornerShape(18.dp),
                    singleLine = true,
                    textStyle = premiumTextFieldStyle(),
                    colors = premiumTextFieldColors()
                )
                OutlinedTextField(
                    value = state.riskPct,
                    onValueChange = viewModel::onRiskPctChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Risk % per Trade", "درصد ریسک هر معامله")) },
                    shape = RoundedCornerShape(18.dp),
                    singleLine = true,
                    textStyle = premiumTextFieldStyle(),
                    colors = premiumTextFieldColors()
                )
                Button(onClick = viewModel::calculate, modifier = Modifier.fillMaxWidth()) {
                    Text(if (state.loading) t("Calculating...", "در حال محاسبه...") else t("Calculate", "محاسبه"))
                }
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }

            state.result?.let { result ->
                val protectionLabel = when {
                    !result.is_trade_allowed -> t("Blocked", "مسدود")
                    result.stop_distance <= 0.0 -> t("Invalid", "نامعتبر")
                    result.position_size_units > 0.0 -> t("Ready", "آماده")
                    else -> t("Observe", "فقط مشاهده")
                }

                PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
                    Text(t("Risk Result", "نتیجه مدیریت ریسک"), color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        RiskChip(t("Trade", "معامله"), if (result.is_trade_allowed) t("Allowed", "مجاز") else t("Blocked", "مسدود"), Modifier.weight(1f))
                        RiskChip(t("Protection", "محافظت"), protectionLabel, Modifier.weight(1f))
                        RiskChip(t("BE RR", "بریک‌اون RR"), result.breakeven_rr.toString(), Modifier.weight(1f))
                    }
                    MetricLine(t("Base / Adjusted Risk", "ریسک پایه / تعدیل‌شده"), "${result.base_risk_amount} / ${result.risk_amount}")
                    MetricLine(t("Position Size Units", "حجم پوزیشن"), result.position_size_units.toString())
                    MetricLine(t("Stop / Effective Stop", "استاپ / استاپ مؤثر"), "${result.stop_distance} / ${result.effective_stop_distance}")
                    MetricLine(t("Portfolio Heat", "حرارت پرتفوی"), "${result.portfolio_heat_pct}%")
                    MetricLine(t("Correlated Risk", "ریسک همبسته"), "${result.correlated_risk_pct}% • ${result.correlation_source}")
                    MetricLine(t("Risk Budget Remaining", "بودجه ریسک باقی‌مانده"), result.risk_budget_remaining.toString())
                    MetricLine(t("DD / Vol Multipliers", "ضریب دراودان / نوسان"), "${result.drawdown_risk_multiplier} / ${result.volatility_risk_multiplier}")
                    MetricLine(t("Partial TPs", "تی‌پی‌های پله‌ای"), result.partial_take_profit_rr.joinToString())
                    if (result.failed_gates.isNotEmpty()) {
                        Text(t("Failed hard gates", "گیت‌های سخت ردشده") + ": ${result.failed_gates.joinToString()}", color = Color(0xFFFF8A8A))
                    }
                    if (result.warnings.isNotEmpty()) {
                        Text(t("Warnings", "هشدارها") + ": ${result.warnings.joinToString()}", color = Color(0xFFFFD27A))
                    }
                }
                PremiumGlassCard(borderColor = Color(0x4059C7FF)) {
                    Text(t("Execution Coaching", "مربی اجرای معامله"), color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(
                        when {
                            !result.is_trade_allowed -> t("Risk engine rejected the setup. Reduce exposure or fix the rule that is blocking execution.", "موتور ریسک این ستاپ را رد کرده است. اکسپوژر را کم کن یا قانونی که اجرا را مسدود کرده اصلاح کن.")
                            riskPctValue > 2.0 -> t("This sizing is aggressive. Use only when setup quality is elite and session conditions are strong.", "این حجم‌گذاری تهاجمی است. فقط وقتی استفاده کن که کیفیت ستاپ ممتاز و شرایط سشن قوی باشد.")
                            result.position_size_units > 0 -> t("Sizing is clean. Align this plan with your execution preview before routing any order.", "حجم‌گذاری تمیز است. قبل از ارسال سفارش، این برنامه را با پیش‌نمایش اجرا هماهنگ کن.")
                            else -> t("Keep refining entry and stop so the command center can produce a precise risk plan.", "ورود و استاپ را دقیق‌تر کن تا مرکز فرمان ریسک بتواند برنامه دقیق‌تری بسازد.")
                        },
                        color = Color(0xFFDDF8FF)
                    )
                }
            }
        }
    }
}

@Composable
private fun RiskChip(title: String, value: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(
                Brush.linearGradient(listOf(Color(0x2611D9FF), Color(0x2217FFB3))),
                RoundedCornerShape(16.dp)
            )
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, color = Color(0xFFBCEEFF), style = MaterialTheme.typography.bodySmall)
            Text(value, color = Color.White, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun MetricLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Color(0xFFDDF8FF))
        Text(value, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
    }
}
