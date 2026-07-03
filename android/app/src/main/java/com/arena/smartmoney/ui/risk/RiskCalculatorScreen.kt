package com.arena.smartmoney.ui.risk

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.components.PremiumGlassCard
import com.arena.smartmoney.ui.components.PremiumScreenBackground
import com.arena.smartmoney.ui.components.PremiumSectionHeader
import com.arena.smartmoney.ui.i18n.rememberTranslator

@Composable
fun RiskCalculatorScreen(viewModel: RiskCalculatorViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    PremiumScreenBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            PremiumSectionHeader(
                title = t("Professional Risk Manager", "مدیریت حرفه‌ای ریسک"),
                subtitle = t(
                    "Position size, max loss, breakeven and partial TP planning.",
                    "محاسبه حجم، حداکثر ضرر، بریک‌اون و برنامه‌ریزی تی‌پی پله‌ای."
                )
            )

            PremiumGlassCard {
                OutlinedTextField(
                    value = state.entry,
                    onValueChange = viewModel::onEntryChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Entry Price", "قیمت ورود")) },
                    shape = RoundedCornerShape(18.dp)
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = state.stop,
                    onValueChange = viewModel::onStopChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Stop Loss", "حد ضرر")) },
                    shape = RoundedCornerShape(18.dp)
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = state.balance,
                    onValueChange = viewModel::onBalanceChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Account Balance", "بالانس حساب")) },
                    shape = RoundedCornerShape(18.dp)
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = state.riskPct,
                    onValueChange = viewModel::onRiskPctChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(t("Risk % per Trade", "درصد ریسک هر معامله")) },
                    shape = RoundedCornerShape(18.dp)
                )
                Spacer(Modifier.height(12.dp))
                Button(onClick = viewModel::calculate, modifier = Modifier.fillMaxWidth()) {
                    Text(if (state.loading) t("Calculating...", "در حال محاسبه...") else t("Calculate", "محاسبه"))
                }
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }

            state.result?.let { result ->
                PremiumGlassCard(borderColor = Color(0x4033E6A6)) {
                    Text(t("Risk Result", "نتیجه مدیریت ریسک"), color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(t("Trade Allowed", "معامله مجاز") + ": ${result.is_trade_allowed}", color = Color.White)
                    Text(t("Risk Amount", "مقدار ریسک") + ": ${result.risk_amount}", color = Color.White)
                    Text(t("Position Size Units", "حجم پوزیشن") + ": ${result.position_size_units}", color = Color.White)
                    Text(t("Stop Distance", "فاصله حد ضرر") + ": ${result.stop_distance}", color = Color.White)
                    Text(t("Breakeven RR", "نسبت بریک‌اون") + ": ${result.breakeven_rr}", color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
                    Text(t("Partial TPs", "تی‌پی‌های پله‌ای") + ": ${result.partial_take_profit_rr.joinToString()}", color = Color(0xFF67ECFF))
                    if (result.warnings.isNotEmpty()) {
                        Text(t("Warnings", "هشدارها") + ": ${result.warnings.joinToString()}", color = Color(0xFFFFD27A))
                    }
                }
            }
        }
    }
}
