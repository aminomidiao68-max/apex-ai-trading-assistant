package com.arena.smartmoney.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arena.smartmoney.ui.i18n.localizeBackendStatus
import com.arena.smartmoney.ui.i18n.localizeMarketQuality
import com.arena.smartmoney.ui.i18n.localizeSessionName
import com.arena.smartmoney.ui.i18n.rememberTranslator
import java.util.Locale
import kotlin.math.abs

@Composable
fun DashboardScreen(
    onOpenBacktest: () -> Unit,
    onOpenAnalytics: () -> Unit,
    viewModel: DashboardViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val t = rememberTranslator()

    val listToShow = if (state.watchlist.isEmpty()) {
        state.watchlistSymbols.map {
            com.arena.smartmoney.data.model.MarketOverviewItem(
                symbol = it,
                market = if (it.endsWith("USDT")) "crypto" else "forex",
                last_price = null,
                change_pct = null,
                source = "offline",
                status = "waiting_for_backend"
            )
        }
    } else state.watchlist

    val strongestSymbol = listToShow.filter { it.change_pct != null }.maxByOrNull { abs(it.change_pct ?: 0.0) }
    val strongestMove = abs(strongestSymbol?.change_pct ?: 0.0)
    val streamInFallbackMode = state.streamStatus.contains("404") || state.streamStatus.contains("error", ignoreCase = true)
    val missingForexFeeds = listToShow.any { it.status == "missing_api_key" }
    val stats = state.tradeStats

    val cryptoAssets = listToShow.count { it.market.equals("crypto", ignoreCase = true) }
    val forexAssets = listToShow.count { it.market.equals("forex", ignoreCase = true) }
    val risingAssets = listToShow.count { (it.change_pct ?: 0.0) > 0.0 }
    val fallingAssets = listToShow.count { (it.change_pct ?: 0.0) < 0.0 }
    val neutralAssets = listToShow.size - risingAssets - fallingAssets

    val focusHealth = focusHealthLabel(state.sessionScore, strongestMove, streamInFallbackMode, t)
    val portfolioHealth = portfolioHealthLabel(
        winRate = stats?.win_rate ?: 0.0,
        openTrades = stats?.open_trades ?: 0,
        netPnl = stats?.net_pnl ?: 0.0,
        assetsTracked = listToShow.size,
        t = t
    )
    val riskPressure = riskPressureLabel(
        openTrades = stats?.open_trades ?: 0,
        netPnl = stats?.net_pnl ?: 0.0,
        t = t
    )
    val breadthHealth = breadthHealthLabel(risingAssets, fallingAssets, neutralAssets, t)
    val scalpAlert = alertStateLabel(state.sessionScore >= 8.0 && strongestMove >= 0.75 && !streamInFallbackMode, t)
    val intradayAlert = alertStateLabel(state.sessionScore >= 6.5 && strongestMove >= 0.35, t)
    val macroAlert = alertStateLabel(strongestMove >= 1.0 || missingForexFeeds, t)
    val executiveHealth = executiveHealthLabel(
        sessionScore = state.sessionScore,
        portfolioHealth = portfolioHealth,
        focusHealth = focusHealth,
        streamFallback = streamInFallbackMode,
        t = t
    )
    val commandPriority = commandPriorityLabel(
        strongestMove = strongestMove,
        openTrades = stats?.open_trades ?: 0,
        risingAssets = risingAssets,
        fallingAssets = fallingAssets,
        t = t
    )
    val missionStatus = missionStatusLabel(
        sessionScore = state.sessionScore,
        streamFallback = streamInFallbackMode,
        openTrades = stats?.open_trades ?: 0,
        t = t
    )
    val executionClimate = executionClimateLabel(
        strongestMove = strongestMove,
        focusHealth = focusHealth,
        riskPressure = riskPressure,
        t = t
    )

    val allocationBias = allocationBiasLabel(cryptoAssets, forexAssets, t)
    val exposureState = exposureStateLabel(stats?.open_trades ?: 0, listToShow.size, t)
    val rotationBias = rotationBiasLabel(risingAssets, fallingAssets, strongestMove, t)
    val capitalDefense = capitalDefenseLabel(stats?.net_pnl ?: 0.0, stats?.open_trades ?: 0, t)

    val quantReadiness = quantReadinessLabel(
        sessionScore = state.sessionScore,
        strongestMove = strongestMove,
        streamFallback = streamInFallbackMode,
        breadthHealth = breadthHealth,
        t = t
    )
    val edgeScore = edgeScoreValue(
        sessionScore = state.sessionScore,
        strongestMove = strongestMove,
        risingAssets = risingAssets,
        fallingAssets = fallingAssets,
        openTrades = stats?.open_trades ?: 0
    )
    val volatilityState = volatilityStateLabel(strongestMove, t)
    val decisionBias = decisionBiasLabel(risingAssets, fallingAssets, strongestMove, t)
    val actionBias = actionBiasLabel(commandPriority, riskPressure, t)
    val confirmationLayer = confirmationLayerLabel(focusHealth, breadthHealth, streamInFallbackMode, t)

    val primeCockpitState = primeCockpitStateLabel(
        sessionScore = state.sessionScore,
        strongestMove = strongestMove,
        streamFallback = streamInFallbackMode,
        t = t
    )
    val executionWindow = executionWindowLabel(
        sessionScore = state.sessionScore,
        strongestMove = strongestMove,
        t = t
    )
    val signalRadarBias = signalRadarBiasLabel(
        risingAssets = risingAssets,
        fallingAssets = fallingAssets,
        strongestMove = strongestMove,
        t = t
    )
    val signalRadarReadiness = signalRadarReadinessLabel(
        sessionScore = state.sessionScore,
        strongestMove = strongestMove,
        streamFallback = streamInFallbackMode,
        breadthHealth = breadthHealth,
        t = t
    )
    val signalPressure = signalPressureLabel(
        openTrades = stats?.open_trades ?: 0,
        riskPressure = riskPressure,
        t = t
    )

    val institutionalState = institutionalStateLabel(
        portfolioHealth = portfolioHealth,
        breadthHealth = breadthHealth,
        streamFallback = streamInFallbackMode,
        t = t
    )
    val tacticalResponse = tacticalResponseLabel(
        commandPriority = commandPriority,
        riskPressure = riskPressure,
        t = t
    )
    val tacticalTempo = tacticalTempoLabel(
        sessionScore = state.sessionScore,
        strongestMove = strongestMove,
        t = t
    )
    val tacticalDefense = tacticalDefenseLabel(
        capitalDefense = capitalDefense,
        riskPressure = riskPressure,
        t = t
    )

    val supremeState = supremeStateLabel(
        executiveHealth = executiveHealth,
        quantReadiness = quantReadiness,
        riskPressure = riskPressure,
        t = t
    )
    val commandShield = commandShieldLabel(
        capitalDefense = capitalDefense,
        riskPressure = riskPressure,
        t = t
    )
    val globalPulseState = globalPulseStateLabel(
        risingAssets = risingAssets,
        fallingAssets = fallingAssets,
        strongestMove = strongestMove,
        t = t
    )
    val pulseVelocity = pulseVelocityLabel(
        strongestMove = strongestMove,
        sessionScore = state.sessionScore,
        t = t
    )

    val finalReadiness = finalReadinessLabel(
        executiveHealth = executiveHealth,
        quantReadiness = quantReadiness,
        signalRadarReadiness = signalRadarReadiness,
        t = t
    )
    val commandPosture = commandPostureLabel(
        commandPriority = commandPriority,
        actionBias = actionBias,
        t = t
    )
    val signalGovernance = signalGovernanceLabel(
        signalPressure = signalPressure,
        riskPressure = riskPressure,
        t = t
    )
    val marketRegime = marketRegimeLabel(
        breadthHealth = breadthHealth,
        globalPulseState = globalPulseState,
        t = t
    )
    val capitalStability = capitalStabilityLabel(
        portfolioHealth = portfolioHealth,
        capitalDefense = capitalDefense,
        t = t
    )
    val executiveAlignment = executiveAlignmentLabel(
        focusHealth = focusHealth,
        breadthHealth = breadthHealth,
        confirmationLayer = confirmationLayer,
        t = t
    )

    val aiSummary = buildString {
        append(
            if (state.sessionScore >= 8.0) {
                t(
                    "AI market engine sees strong session quality and active movement.",
                    "موتور هوش مصنوعی کیفیت خوب سشن و حرکت فعال بازار را تشخیص می‌دهد."
                )
            } else {
                t(
                    "AI market engine sees moderate conditions; be more selective.",
                    "موتور هوش مصنوعی شرایط متوسط بازار را تشخیص می‌دهد؛ انتخاب معامله باید گزینشی‌تر باشد."
                )
            }
        )
        strongestSymbol?.let {
            append(" ")
            append(
                t(
                    "Focus symbol: ${it.symbol} (${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)}%).",
                    "نماد مهم فعلی: ${it.symbol} (${String.format(Locale.US, "%.2f", it.change_pct ?: 0.0)}%)."
                )
            )
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        Color(0xFF050B14),
                        Color(0xFF08131F),
                        Color(0xFF0B1D2B),
                        Color(0xFF050B14)
                    )
                )
            )
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                NeonPanel(
                    brush = Brush.linearGradient(
                        listOf(Color(0xFF0B1320), Color(0xFF11263B), Color(0xFF0B1320))
                    )
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            text = "APEX AI PREMIUM",
                            style = MaterialTheme.typography.headlineMedium,
                            color = Color(0xFF67ECFF),
                            fontWeight = FontWeight.ExtraBold
                        )
                        Text(
                            text = t("Mission Control", "مرکز عملیات"),
                            color = Color.White,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Created by Amin omidi",
                            color = Color(0xFF9BEFFF),
                            style = MaterialTheme.typography.titleSmall
                        )
                        Text(
                            text = aiSummary,
                            color = Color(0xFFE3F8FF),
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            InfoChip(t("Session", "سشن"), localizeSessionName(state.sessionName, t))
                            InfoChip(t("Quality", "کیفیت"), localizeMarketQuality(state.marketQuality, t))
                            InfoChip(t("Score", "امتیاز"), String.format(Locale.US, "%.1f", state.sessionScore))
                        }
                    }
                }
            }

            item {
                MissionControlBoard(
                    missionStatus = missionStatus,
                    commandPriority = commandPriority,
                    executionClimate = executionClimate,
                    t = t
                )
            }

            item {
                SupremeControlLayerBoard(
                    supremeState = supremeState,
                    commandShield = commandShield,
                    pulseVelocity = pulseVelocity,
                    t = t
                )
            }

            item {
                GlobalMarketPulseBoard(
                    globalPulseState = globalPulseState,
                    strongestSymbol = strongestSymbol?.symbol ?: "-",
                    strongestMove = strongestMove,
                    allocationBias = allocationBias,
                    t = t
                )
            }

            item {
                InstitutionalAIMatrixBoard(
                    finalReadiness = finalReadiness,
                    commandPosture = commandPosture,
                    signalGovernance = signalGovernance,
                    t = t
                )
            }

            item {
                FinalExecutiveLayerBoard(
                    marketRegime = marketRegime,
                    capitalStability = capitalStability,
                    executiveAlignment = executiveAlignment,
                    t = t
                )
            }

            item {
                PrimeAICockpitBoard(
                    primeCockpitState = primeCockpitState,
                    executionWindow = executionWindow,
                    signalPressure = signalPressure,
                    t = t
                )
            }

            item {
                ExecutiveSignalRadarBoard(
                    signalRadarBias = signalRadarBias,
                    signalRadarReadiness = signalRadarReadiness,
                    commandPriority = commandPriority,
                    strongestSymbol = strongestSymbol?.symbol ?: "-",
                    t = t
                )
            }

            item {
                InstitutionalOverviewGrid(
                    institutionalState = institutionalState,
                    allocationBias = allocationBias,
                    breadthHealth = breadthHealth,
                    focusHealth = focusHealth,
                    t = t
                )
            }

            item {
                TacticalResponseBoard(
                    tacticalResponse = tacticalResponse,
                    tacticalTempo = tacticalTempo,
                    tacticalDefense = tacticalDefense,
                    t = t
                )
            }

            item {
                ExecutiveOverviewBoard(
                    executiveHealth = executiveHealth,
                    commandPriority = commandPriority,
                    focusHealth = focusHealth,
                    portfolioHealth = portfolioHealth,
                    breadthHealth = breadthHealth,
                    t = t,
                )
            }

            item {
                QuantOpsCenterBoard(
                    quantReadiness = quantReadiness,
                    edgeScore = edgeScore,
                    volatilityState = volatilityState,
                    t = t
                )
            }

            item {
                AdvancedDecisionMatrixBoard(
                    decisionBias = decisionBias,
                    actionBias = actionBias,
                    confirmationLayer = confirmationLayer,
                    t = t
                )
            }

            item {
                ElitePortfolioFlowBoard(
                    risingAssets = risingAssets,
                    fallingAssets = fallingAssets,
                    neutralAssets = neutralAssets,
                    exposureState = exposureState,
                    rotationBias = rotationBias,
                    strongestSymbol = strongestSymbol?.symbol ?: "-",
                    t = t
                )
            }

            item {
                CapitalAllocationBoard(
                    allocationBias = allocationBias,
                    capitalDefense = capitalDefense,
                    cryptoAssets = cryptoAssets,
                    forexAssets = forexAssets,
                    assetsTracked = listToShow.size,
                    t = t
                )
            }

            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    MetricCard(
                        modifier = Modifier.weight(1f),
                        title = t("Win Rate", "نرخ برد"),
                        value = "${stats?.win_rate ?: 0.0}%",
                        accent = Color(0xFF33E6A6)
                    )
                    MetricCard(
                        modifier = Modifier.weight(1f),
                        title = t("Open Trades", "معاملات باز"),
                        value = "${stats?.open_trades ?: 0}",
                        accent = Color(0xFF59C7FF)
                    )
                    MetricCard(
                        modifier = Modifier.weight(1f),
                        title = t("Net PnL", "سود خالص"),
                        value = String.format(Locale.US, "%.2f", stats?.net_pnl ?: 0.0),
                        accent = if ((stats?.net_pnl ?: 0.0) >= 0) Color(0xFF67ECFF) else Color(0xFFFF7A7A)
                    )
                }
            }

            item {
                PortfolioCommandBoard(
                    assetsTracked = listToShow.size,
                    cryptoAssets = cryptoAssets,
                    forexAssets = forexAssets,
                    portfolioHealth = portfolioHealth,
                    riskPressure = riskPressure,
                    t = t
                )
            }

            item {
                MultiAssetIntelligenceBoard(
                    risingAssets = risingAssets,
                    fallingAssets = fallingAssets,
                    neutralAssets = neutralAssets,
                    strongestSymbol = strongestSymbol?.symbol ?: "-",
                    strongestMove = strongestMove,
                    t = t
                )
            }

            item {
                MarketFocusBoard(
                    strongestSymbol = strongestSymbol,
                    focusHealth = focusHealth,
                    streamInFallbackMode = streamInFallbackMode,
                    missingForexFeeds = missingForexFeeds,
                    t = t,
                )
            }

            item {
                SmartAlertsBoard(
                    scalpAlert = scalpAlert,
                    intradayAlert = intradayAlert,
                    macroAlert = macroAlert,
                    t = t,
                )
            }

            item {
                Text(
                    text = t("Premium AI Modules", "ماژول‌های پرمیوم هوش مصنوعی"),
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }

            item {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ActionCard(
                        modifier = Modifier.weight(1f),
                        title = t("Backtest Lab", "آزمایشگاه بک‌تست"),
                        subtitle = t("Validate setup quality", "اعتبارسنجی کیفیت ستاپ"),
                        accent = listOf(Color(0xFF1B7CFF), Color(0xFF33D6FF)),
                        onClick = onOpenBacktest
                    )
                    ActionCard(
                        modifier = Modifier.weight(1f),
                        title = t("Analytics Center", "مرکز آنالیتیکس"),
                        subtitle = t("Review signal performance", "بررسی عملکرد سیگنال‌ها"),
                        accent = listOf(Color(0xFF00C78C), Color(0xFF67ECFF)),
                        onClick = onOpenAnalytics
                    )
                }
            }

            item {
                NeonPanel(
                    brush = Brush.linearGradient(
                        listOf(Color(0xFF111A29), Color(0xFF13263A), Color(0xFF111A29))
                    )
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            text = t("Live Market Stream", "استریم زنده بازار"),
                            style = MaterialTheme.typography.titleLarge,
                            color = Color.White,
                            fontWeight = FontWeight.Bold
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            StreamChip("BTC", onClick = { viewModel.selectStreamSymbol("BTCUSDT") })
                            StreamChip("ETH", onClick = { viewModel.selectStreamSymbol("ETHUSDT") })
                            StreamChip("EURUSD", onClick = { viewModel.selectStreamSymbol("EURUSD") })
                            StreamChip("XAU", onClick = { viewModel.selectStreamSymbol("XAUUSD") })
                        }
                        Button(onClick = { viewModel.reconnectStream() }, modifier = Modifier.fillMaxWidth()) {
                            Text(t("Reconnect Live Feed", "اتصال مجدد فید زنده"))
                        }
                        Text(
                            text = t("Focused symbol", "نماد انتخابی") + ": ${state.streamSymbol}",
                            color = Color(0xFFB9F3FF)
                        )
                        Text(
                            text = if (streamInFallbackMode) {
                                t(
                                    "Realtime websocket is unavailable right now. REST fallback is keeping the dashboard live.",
                                    "فعلاً وب‌سوکت لحظه‌ای در دسترس نیست اما حالت جایگزین REST داشبورد را زنده نگه داشته است."
                                )
                            } else {
                                t(
                                    "Realtime stream is connected and feeding the dashboard.",
                                    "استریم لحظه‌ای متصل است و داده را به داشبورد می‌رساند."
                                )
                            },
                            color = if (streamInFallbackMode) Color(0xFFFFD27A) else Color(0xFF67ECFF)
                        )
                        state.liveSnapshot?.let {
                            Text(
                                text = t("Live price", "قیمت لحظه‌ای") + ": ${it.last_price ?: "-"} • 24h: ${it.change_pct ?: "-"}% • ${localizeBackendStatus(it.status, t)}",
                                color = when {
                                    (it.change_pct ?: 0.0) > 0 -> Color(0xFF33E6A6)
                                    (it.change_pct ?: 0.0) < 0 -> Color(0xFFFF7A7A)
                                    else -> Color.White
                                },
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }

            if (missingForexFeeds) {
                item {
                    NeonPanel(
                        brush = Brush.linearGradient(
                            listOf(Color(0xFF241915), Color(0xFF322216), Color(0xFF241915))
                        ),
                        borderColor = Color(0x55FFB657)
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                text = t("Forex Feed Notice", "هشدار فید فارکس"),
                                color = Color(0xFFFFD27A),
                                fontWeight = FontWeight.Bold,
                                style = MaterialTheme.typography.titleMedium
                            )
                            Text(
                                text = t(
                                    "Forex and gold remain limited until TwelveData API key is configured on the backend.",
                                    "داده فارکس و طلا تا زمان تنظیم کلید TwelveData روی بک‌اند محدود باقی می‌ماند."
                                ),
                                color = Color.White
                            )
                        }
                    }
                }
            }

            item {
                Text(
                    text = t("Live Watchlist", "واچ‌لیست زنده"),
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }

            items(listToShow) { item ->
                WatchlistCard(item = item, t = t)
            }
        }
    }
}

private fun focusHealthLabel(sessionScore: Double, strongestMove: Double, streamFallback: Boolean, t: (String, String) -> String): String {
    return when {
        sessionScore >= 8.0 && strongestMove >= 0.75 && !streamFallback -> t("Elite", "ممتاز")
        sessionScore >= 6.5 && strongestMove >= 0.35 -> t("Strong", "قوی")
        sessionScore >= 5.0 -> t("Developing", "در حال شکل‌گیری")
        else -> t("Weak", "ضعیف")
    }
}

private fun alertStateLabel(isReady: Boolean, t: (String, String) -> String): String {
    return if (isReady) t("Armed", "مسلح") else t("Standby", "آماده‌باش")
}

private fun portfolioHealthLabel(
    winRate: Double,
    openTrades: Int,
    netPnl: Double,
    assetsTracked: Int,
    t: (String, String) -> String,
): String {
    return when {
        winRate >= 58.0 && netPnl > 0 && assetsTracked >= 4 -> t("Elite", "ممتاز")
        winRate >= 48.0 && assetsTracked >= 3 -> t("Strong", "قوی")
        openTrades > 0 || assetsTracked > 0 -> t("Developing", "در حال شکل‌گیری")
        else -> t("Idle", "بدون داده")
    }
}

private fun riskPressureLabel(
    openTrades: Int,
    netPnl: Double,
    t: (String, String) -> String,
): String {
    return when {
        openTrades >= 3 || netPnl < 0 -> t("High", "بالا")
        openTrades >= 1 -> t("Moderate", "متوسط")
        else -> t("Low", "پایین")
    }
}

private fun breadthHealthLabel(
    risingAssets: Int,
    fallingAssets: Int,
    neutralAssets: Int,
    t: (String, String) -> String,
): String {
    return when {
        risingAssets > fallingAssets && risingAssets >= 2 -> t("Bullish", "صعودی")
        fallingAssets > risingAssets && fallingAssets >= 2 -> t("Bearish", "نزولی")
        neutralAssets > 0 -> t("Balanced", "متعادل")
        else -> t("Mixed", "ترکیبی")
    }
}

private fun executiveHealthLabel(
    sessionScore: Double,
    portfolioHealth: String,
    focusHealth: String,
    streamFallback: Boolean,
    t: (String, String) -> String,
): String {
    return when {
        sessionScore >= 8.0 && !streamFallback && (portfolioHealth == t("Elite", "ممتاز") || focusHealth == t("Elite", "ممتاز")) -> t("Prime", "درجه یک")
        sessionScore >= 6.5 && !streamFallback -> t("Strong", "قوی")
        streamFallback -> t("Protected", "محافظت‌شده")
        else -> t("Measured", "کنترل‌شده")
    }
}

private fun commandPriorityLabel(
    strongestMove: Double,
    openTrades: Int,
    risingAssets: Int,
    fallingAssets: Int,
    t: (String, String) -> String,
): String {
    return when {
        strongestMove >= 1.0 && openTrades == 0 -> t("Deploy", "استقرار")
        strongestMove >= 0.5 && risingAssets != fallingAssets -> t("Monitor", "پایش")
        openTrades >= 3 -> t("Defend", "دفاع")
        else -> t("Observe", "مشاهده")
    }
}

private fun missionStatusLabel(
    sessionScore: Double,
    streamFallback: Boolean,
    openTrades: Int,
    t: (String, String) -> String,
): String {
    return when {
        sessionScore >= 8.0 && !streamFallback && openTrades <= 2 -> t("Active", "فعال")
        streamFallback -> t("Protected", "محافظت‌شده")
        else -> t("Measured", "کنترل‌شده")
    }
}

private fun executionClimateLabel(
    strongestMove: Double,
    focusHealth: String,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        strongestMove >= 0.75 && focusHealth == t("Elite", "ممتاز") && riskPressure != t("High", "بالا") -> t("Aggressive", "تهاجمی")
        strongestMove >= 0.35 -> t("Balanced", "متعادل")
        else -> t("Conservative", "محافظه‌کار")
    }
}

private fun allocationBiasLabel(
    cryptoAssets: Int,
    forexAssets: Int,
    t: (String, String) -> String,
): String {
    return when {
        cryptoAssets > forexAssets -> t("Crypto Led", "کریپتو‌محور")
        forexAssets > cryptoAssets -> t("Forex Led", "فارکس‌محور")
        cryptoAssets == 0 && forexAssets == 0 -> t("Idle", "بدون داده")
        else -> t("Balanced", "متعادل")
    }
}

private fun exposureStateLabel(
    openTrades: Int,
    assetsTracked: Int,
    t: (String, String) -> String,
): String {
    return when {
        openTrades >= 3 -> t("Loaded", "سنگین")
        openTrades >= 1 && assetsTracked >= 3 -> t("Engaged", "درگیر")
        assetsTracked > 0 -> t("Light", "سبک")
        else -> t("Idle", "بدون داده")
    }
}

private fun rotationBiasLabel(
    risingAssets: Int,
    fallingAssets: Int,
    strongestMove: Double,
    t: (String, String) -> String,
): String {
    return when {
        strongestMove >= 1.0 && risingAssets > fallingAssets -> t("Risk-On", "ریسک‌پذیر")
        strongestMove >= 1.0 && fallingAssets > risingAssets -> t("Risk-Off", "ریسک‌گریز")
        risingAssets == fallingAssets -> t("Balanced", "متعادل")
        else -> t("Transition", "در حال چرخش")
    }
}

private fun capitalDefenseLabel(
    netPnl: Double,
    openTrades: Int,
    t: (String, String) -> String,
): String {
    return when {
        netPnl < 0 && openTrades >= 2 -> t("Defend", "دفاع")
        netPnl >= 0 && openTrades <= 1 -> t("Preserved", "حفظ‌شده")
        else -> t("Managed", "مدیریت‌شده")
    }
}

private fun quantReadinessLabel(
    sessionScore: Double,
    strongestMove: Double,
    streamFallback: Boolean,
    breadthHealth: String,
    t: (String, String) -> String,
): String {
    return when {
        sessionScore >= 8.0 && strongestMove >= 0.75 && !streamFallback && breadthHealth == t("Bullish", "صعودی") -> t("Prime", "درجه یک")
        sessionScore >= 6.5 && strongestMove >= 0.35 && !streamFallback -> t("Ready", "آماده")
        streamFallback -> t("Protected", "محافظت‌شده")
        else -> t("Building", "در حال ساخت")
    }
}

private fun edgeScoreValue(
    sessionScore: Double,
    strongestMove: Double,
    risingAssets: Int,
    fallingAssets: Int,
    openTrades: Int,
): String {
    val raw = (sessionScore * 6.0) + (strongestMove * 18.0) + ((risingAssets - fallingAssets) * 2.0) - (openTrades * 3.0)
    val bounded = raw.coerceIn(0.0, 100.0)
    return String.format(Locale.US, "%.0f", bounded)
}

private fun volatilityStateLabel(
    strongestMove: Double,
    t: (String, String) -> String,
): String {
    return when {
        strongestMove >= 1.0 -> t("Expanded", "منبسط")
        strongestMove >= 0.45 -> t("Tradable", "قابل معامله")
        strongestMove > 0.0 -> t("Compressed", "فشرده")
        else -> t("Flat", "فلت")
    }
}

private fun decisionBiasLabel(
    risingAssets: Int,
    fallingAssets: Int,
    strongestMove: Double,
    t: (String, String) -> String,
): String {
    return when {
        risingAssets > fallingAssets && strongestMove >= 0.5 -> t("Bullish", "صعودی")
        fallingAssets > risingAssets && strongestMove >= 0.5 -> t("Bearish", "نزولی")
        else -> t("Neutral", "خنثی")
    }
}

private fun actionBiasLabel(
    commandPriority: String,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        commandPriority == t("Deploy", "استقرار") && riskPressure != t("High", "بالا") -> t("Execute", "اجرا")
        commandPriority == t("Monitor", "پایش") -> t("Prepare", "آماده‌سازی")
        riskPressure == t("High", "بالا") -> t("Defend", "دفاع")
        else -> t("Observe", "مشاهده")
    }
}

private fun confirmationLayerLabel(
    focusHealth: String,
    breadthHealth: String,
    streamInFallbackMode: Boolean,
    t: (String, String) -> String,
): String {
    return when {
        !streamInFallbackMode && focusHealth == t("Elite", "ممتاز") && breadthHealth != t("Mixed", "ترکیبی") -> t("Confirmed", "تأییدشده")
        !streamInFallbackMode -> t("Partial", "نیمه‌تأیید")
        else -> t("Protected", "محافظت‌شده")
    }
}

private fun primeCockpitStateLabel(
    sessionScore: Double,
    strongestMove: Double,
    streamFallback: Boolean,
    t: (String, String) -> String,
): String {
    return when {
        sessionScore >= 8.0 && strongestMove >= 0.75 && !streamFallback -> t("Prime", "درجه یک")
        sessionScore >= 6.5 && strongestMove >= 0.35 -> t("Armed", "مسلح")
        streamFallback -> t("Protected", "محافظت‌شده")
        else -> t("Building", "در حال ساخت")
    }
}

private fun executionWindowLabel(
    sessionScore: Double,
    strongestMove: Double,
    t: (String, String) -> String,
): String {
    return when {
        sessionScore >= 8.0 && strongestMove >= 0.75 -> t("Fast", "سریع")
        sessionScore >= 6.5 && strongestMove >= 0.35 -> t("Active", "فعال")
        strongestMove > 0.0 -> t("Selective", "انتخابی")
        else -> t("Quiet", "آرام")
    }
}

private fun signalRadarBiasLabel(
    risingAssets: Int,
    fallingAssets: Int,
    strongestMove: Double,
    t: (String, String) -> String,
): String {
    return when {
        strongestMove >= 0.5 && risingAssets > fallingAssets -> t("Bull Dominant", "غلبه خریداران")
        strongestMove >= 0.5 && fallingAssets > risingAssets -> t("Bear Dominant", "غلبه فروشندگان")
        else -> t("Two-Way", "دوطرفه")
    }
}

private fun signalRadarReadinessLabel(
    sessionScore: Double,
    strongestMove: Double,
    streamFallback: Boolean,
    breadthHealth: String,
    t: (String, String) -> String,
): String {
    return when {
        sessionScore >= 8.0 && strongestMove >= 0.75 && !streamFallback && breadthHealth != t("Mixed", "ترکیبی") -> t("Ready", "آماده")
        !streamFallback -> t("Tracking", "در حال ردیابی")
        else -> t("Protected", "محافظت‌شده")
    }
}

private fun signalPressureLabel(
    openTrades: Int,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        openTrades >= 3 || riskPressure == t("High", "بالا") -> t("Elevated", "بالارفته")
        openTrades >= 1 -> t("Managed", "مدیریت‌شده")
        else -> t("Light", "سبک")
    }
}

private fun institutionalStateLabel(
    portfolioHealth: String,
    breadthHealth: String,
    streamFallback: Boolean,
    t: (String, String) -> String,
): String {
    return when {
        !streamFallback && portfolioHealth == t("Elite", "ممتاز") && breadthHealth != t("Mixed", "ترکیبی") -> t("Aligned", "همسو")
        !streamFallback -> t("Stable", "پایدار")
        else -> t("Protected", "محافظت‌شده")
    }
}

private fun tacticalResponseLabel(
    commandPriority: String,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        commandPriority == t("Deploy", "استقرار") && riskPressure != t("High", "بالا") -> t("Push", "پیشروی")
        commandPriority == t("Defend", "دفاع") || riskPressure == t("High", "بالا") -> t("Shield", "حفاظت")
        else -> t("Track", "ردیابی")
    }
}

private fun tacticalTempoLabel(
    sessionScore: Double,
    strongestMove: Double,
    t: (String, String) -> String,
): String {
    return when {
        sessionScore >= 8.0 && strongestMove >= 0.75 -> t("Fast", "سریع")
        sessionScore >= 6.5 && strongestMove >= 0.35 -> t("Measured", "کنترل‌شده")
        else -> t("Slow", "آهسته")
    }
}

private fun tacticalDefenseLabel(
    capitalDefense: String,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        capitalDefense == t("Defend", "دفاع") || riskPressure == t("High", "بالا") -> t("High Guard", "دفاع بالا")
        capitalDefense == t("Managed", "مدیریت‌شده") -> t("Medium Guard", "دفاع متوسط")
        else -> t("Low Guard", "دفاع پایین")
    }
}

private fun supremeStateLabel(
    executiveHealth: String,
    quantReadiness: String,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        executiveHealth == t("Prime", "درجه یک") && quantReadiness == t("Prime", "درجه یک") && riskPressure != t("High", "بالا") -> t("Supreme", "برتر")
        executiveHealth == t("Strong", "قوی") || quantReadiness == t("Ready", "آماده") -> t("Command", "فرمان")
        else -> t("Guarded", "محافظت‌شده")
    }
}

private fun commandShieldLabel(
    capitalDefense: String,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        capitalDefense == t("Defend", "دفاع") || riskPressure == t("High", "بالا") -> t("Heavy", "سنگین")
        capitalDefense == t("Managed", "مدیریت‌شده") -> t("Medium", "متوسط")
        else -> t("Light", "سبک")
    }
}

private fun globalPulseStateLabel(
    risingAssets: Int,
    fallingAssets: Int,
    strongestMove: Double,
    t: (String, String) -> String,
): String {
    return when {
        strongestMove >= 1.0 && risingAssets > fallingAssets -> t("Risk-On", "ریسک‌پذیر")
        strongestMove >= 1.0 && fallingAssets > risingAssets -> t("Risk-Off", "ریسک‌گریز")
        strongestMove >= 0.35 -> t("Active", "فعال")
        else -> t("Quiet", "آرام")
    }
}

private fun pulseVelocityLabel(
    strongestMove: Double,
    sessionScore: Double,
    t: (String, String) -> String,
): String {
    return when {
        strongestMove >= 1.0 && sessionScore >= 8.0 -> t("Explosive", "انفجاری")
        strongestMove >= 0.5 -> t("Fast", "سریع")
        strongestMove > 0.0 -> t("Measured", "کنترل‌شده")
        else -> t("Slow", "آهسته")
    }
}

private fun finalReadinessLabel(
    executiveHealth: String,
    quantReadiness: String,
    signalRadarReadiness: String,
    t: (String, String) -> String,
): String {
    return when {
        executiveHealth == t("Prime", "درجه یک") && quantReadiness == t("Prime", "درجه یک") && signalRadarReadiness == t("Ready", "آماده") -> t("Ready", "آماده")
        quantReadiness == t("Ready", "آماده") || signalRadarReadiness == t("Tracking", "در حال ردیابی") -> t("Near Ready", "نزدیک به آماده")
        else -> t("Building", "در حال ساخت")
    }
}

private fun commandPostureLabel(
    commandPriority: String,
    actionBias: String,
    t: (String, String) -> String,
): String {
    return when {
        commandPriority == t("Deploy", "استقرار") && actionBias == t("Execute", "اجرا") -> t("Aggressive", "تهاجمی")
        commandPriority == t("Monitor", "پایش") -> t("Adaptive", "تطبیقی")
        else -> t("Defensive", "دفاعی")
    }
}

private fun signalGovernanceLabel(
    signalPressure: String,
    riskPressure: String,
    t: (String, String) -> String,
): String {
    return when {
        signalPressure == t("Elevated", "بالارفته") || riskPressure == t("High", "بالا") -> t("Tight", "سخت‌گیرانه")
        signalPressure == t("Managed", "مدیریت‌شده") -> t("Balanced", "متعادل")
        else -> t("Light", "سبک")
    }
}

private fun marketRegimeLabel(
    breadthHealth: String,
    globalPulseState: String,
    t: (String, String) -> String,
): String {
    return when {
        breadthHealth == t("Bullish", "صعودی") && globalPulseState == t("Risk-On", "ریسک‌پذیر") -> t("Expansion", "گسترش")
        breadthHealth == t("Bearish", "نزولی") && globalPulseState == t("Risk-Off", "ریسک‌گریز") -> t("Contraction", "انقباض")
        else -> t("Transition", "گذار")
    }
}

private fun capitalStabilityLabel(
    portfolioHealth: String,
    capitalDefense: String,
    t: (String, String) -> String,
): String {
    return when {
        portfolioHealth == t("Elite", "ممتاز") && capitalDefense == t("Preserved", "حفظ‌شده") -> t("Stable", "پایدار")
        capitalDefense == t("Managed", "مدیریت‌شده") -> t("Controlled", "کنترل‌شده")
        else -> t("Fragile", "شکننده")
    }
}

private fun executiveAlignmentLabel(
    focusHealth: String,
    breadthHealth: String,
    confirmationLayer: String,
    t: (String, String) -> String,
): String {
    return when {
        focusHealth == t("Elite", "ممتاز") && breadthHealth != t("Mixed", "ترکیبی") && confirmationLayer == t("Confirmed", "تأییدشده") -> t("Aligned", "همسو")
        confirmationLayer == t("Partial", "نیمه‌تأیید") -> t("Partial", "نیمه‌همسو")
        else -> t("Unclear", "نامشخص")
    }
}
