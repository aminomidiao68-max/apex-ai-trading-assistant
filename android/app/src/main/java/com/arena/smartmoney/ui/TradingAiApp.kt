package com.arena.smartmoney.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Calculate
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.core.content.ContextCompat
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavType
import androidx.navigation.navArgument
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.arena.smartmoney.data.preferences.AppPreferencesManager
import com.arena.smartmoney.data.session.SessionManager
import com.arena.smartmoney.push.PushRegistrationHelper
import com.arena.smartmoney.ui.analytics.AnalyticsScreen
import com.arena.smartmoney.ui.auth.AuthScreen
import com.arena.smartmoney.ui.backtest.BacktestScreen
import com.arena.smartmoney.ui.broker.BrokerScreen
import com.arena.smartmoney.ui.chart.ChartScreen
import com.arena.smartmoney.ui.dashboard.DashboardScreen
import com.arena.smartmoney.ui.news.NewsScreen
import com.arena.smartmoney.ui.i18n.AppLanguageState
import com.arena.smartmoney.ui.i18n.rememberTranslator
import com.arena.smartmoney.ui.journal.JournalScreen
import com.arena.smartmoney.ui.market.MarketAnalysisScreen
import com.arena.smartmoney.ui.profile.ProfileScreen
import com.arena.smartmoney.ui.readiness.ReadinessScreen
import com.arena.smartmoney.ui.risk.RiskCalculatorScreen
import com.arena.smartmoney.ui.settings.SettingsScreen
import com.arena.smartmoney.ui.signals.SignalsScreen
import com.arena.smartmoney.ui.setups.TradeSetupsScreen

sealed class AppRoute(val route: String, val label: String) {
    data object Dashboard : AppRoute("dashboard", "Dashboard")
    data object Signals : AppRoute("signals", "Signals")
    data object Chart : AppRoute("chart", "Chart")
    data object Setups : AppRoute("setups", "Trading Setups")
    data object Risk : AppRoute("risk", "Risk")
    data object Broker : AppRoute("broker", "Broker")
    data object Profile : AppRoute("profile", "Profile")
    data object Journal : AppRoute("journal", "Journal")
    data object Backtest : AppRoute("backtest", "Backtest")
    data object Analytics : AppRoute("analytics", "Analytics")
    data object MarketAnalysis : AppRoute("market_analysis", "Market Analysis")
    data object Settings : AppRoute("settings", "Settings")
    data object Readiness : AppRoute("readiness", "Readiness")
}

@Composable
fun TradingAiApp() {
    val context = LocalContext.current
    val sessionManager = remember { SessionManager(context) }
    val prefs = remember { AppPreferencesManager(context) }
    var isLoggedIn by rememberSaveable { mutableStateOf(sessionManager.getToken() != null) }
    RequestNotificationPermissionIfNeeded()

    LaunchedEffect(Unit) {
        AppLanguageState.current = prefs.getLanguage()
    }

    LaunchedEffect(isLoggedIn) {
        if (isLoggedIn) {
            PushRegistrationHelper.registerCurrentDevice(sessionManager)
        }
    }

    val layoutDirection = if (AppLanguageState.current == "fa") LayoutDirection.Rtl else LayoutDirection.Ltr

    CompositionLocalProvider(LocalLayoutDirection provides layoutDirection) {
        if (!isLoggedIn) {
            AuthScreen(onAuthSuccess = { isLoggedIn = true })
        } else {
            TradingMainScaffold(
                onLogout = {
                    sessionManager.clearSession()
                    isLoggedIn = false
                }
            )
        }
    }
}

@Composable
private fun RequestNotificationPermissionIfNeeded() {
    val context = LocalContext.current
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }

    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
}

@Composable
private fun TradingMainScaffold(onLogout: () -> Unit) {
    val navController = rememberNavController()
    val t = rememberTranslator()
    val items = listOf(
        AppRoute.Dashboard,
        AppRoute.Setups,
        AppRoute.Risk,
        AppRoute.Broker,
        AppRoute.Profile
    )

    Scaffold(
        bottomBar = {
            NavigationBar {
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = navBackStackEntry?.destination

                items.forEach { route ->
                    val icon = when (route) {
                        AppRoute.Dashboard -> Icons.Default.Dashboard
                        AppRoute.Signals -> Icons.Default.Analytics
                        AppRoute.Chart -> Icons.Default.ShowChart
                        AppRoute.Setups -> Icons.Default.AutoAwesome
                        AppRoute.Risk -> Icons.Default.Calculate
                        AppRoute.Broker -> Icons.Default.Settings
                        AppRoute.Profile -> Icons.Default.Person
                        AppRoute.Journal -> Icons.Default.Analytics
                        AppRoute.Backtest -> Icons.Default.Analytics
                        AppRoute.Analytics -> Icons.Default.Analytics
                        AppRoute.MarketAnalysis -> Icons.Default.ShowChart
                        AppRoute.Settings -> Icons.Default.Settings
                        AppRoute.Readiness -> Icons.Default.Settings
                    }
                    val localizedLabel = when (route) {
                        AppRoute.Dashboard -> t("Dashboard", "داشبورد")
                        AppRoute.Signals -> t("Signals", "سیگنال‌ها")
                        AppRoute.Chart -> t("Chart", "نمودار")
                        AppRoute.Setups -> t("Setups", "ستاپ‌ها")
                        AppRoute.Risk -> t("Risk", "ریسک")
                        AppRoute.Broker -> t("Broker", "بروکر")
                        AppRoute.Profile -> t("Profile", "پروفایل")
                        AppRoute.Journal -> t("Journal", "ژورنال")
                        AppRoute.Backtest -> t("Backtest", "بک‌تست")
                        AppRoute.Analytics -> t("Analytics", "آنالیتیکس")
                        AppRoute.MarketAnalysis -> t("Market Analysis", "تحلیل بازار")
                        AppRoute.Settings -> t("Settings", "تنظیمات")
                        AppRoute.Readiness -> t("Readiness", "آمادگی")
                    }

                    NavigationBarItem(
                        selected = currentDestination?.hierarchy?.any { it.route == route.route } == true,
                        onClick = {
                            navController.navigate(route.route) {
                                launchSingleTop = true
                                restoreState = true
                                popUpTo(navController.graph.startDestinationId) {
                                    saveState = true
                                }
                            }
                        },
                        icon = { Icon(icon, contentDescription = localizedLabel) },
                        label = { Text(localizedLabel) }
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = AppRoute.Dashboard.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(AppRoute.Dashboard.route) {
                DashboardScreen(
                    onOpenBacktest = { navController.navigate(AppRoute.Backtest.route) },
                    onOpenAnalytics = { navController.navigate(AppRoute.Analytics.route) },
                    onOpenMarketAnalysis = { navController.navigate(AppRoute.MarketAnalysis.route) },
                    onOpenNews = { navController.navigate("news") },
                    onOpenJournal = { navController.navigate(AppRoute.Journal.route) },
                    onOpenSignals = { navController.navigate(AppRoute.Signals.route) },
                    onOpenChart = { navController.navigate(AppRoute.Chart.route) },
                    onOpenSetups = { navController.navigate(AppRoute.Setups.route) }
                )
            }

                composable("news") {
                    NewsScreen(onBack = { navController.popBackStack() })
                }
            composable(AppRoute.Signals.route) {
                SignalsScreen(onOpenJournal = { navController.navigate(AppRoute.Journal.route) })
            }
            composable(AppRoute.Chart.route) { ChartScreen() }
            composable(AppRoute.Setups.route) {
                TradeSetupsScreen(
                    onOpenChart = { symbol, market, timeframe ->
                        navController.navigate("chart/$symbol/$market/$timeframe")
                    }
                )
            }
            composable(
                route = "chart/{symbol}/{market}/{timeframe}",
                arguments = listOf(
                    navArgument("symbol") { type = NavType.StringType },
                    navArgument("market") { type = NavType.StringType },
                    navArgument("timeframe") { type = NavType.StringType },
                ),
            ) { backStackEntry ->
                ChartScreen(
                    onBack = { navController.popBackStack() },
                    initialSymbol = backStackEntry.arguments?.getString("symbol") ?: "XAUUSD",
                    initialMarket = backStackEntry.arguments?.getString("market") ?: "",
                    initialTimeframe = backStackEntry.arguments?.getString("timeframe") ?: "15m",
                )
            }
            composable(AppRoute.Risk.route) { RiskCalculatorScreen() }
            composable(AppRoute.Broker.route) { BrokerScreen() }
            composable(AppRoute.Profile.route) {
                ProfileScreen(
                    onLogout = onLogout,
                    onOpenSettings = { navController.navigate(AppRoute.Settings.route) }
                )
            }
            composable(AppRoute.Journal.route) { JournalScreen() }
            composable(AppRoute.Backtest.route) { BacktestScreen() }
            composable(AppRoute.Analytics.route) { AnalyticsScreen() }
            composable(AppRoute.MarketAnalysis.route) {
                MarketAnalysisScreen(
                    onOpenChart = { navController.navigate(AppRoute.Chart.route) },
                    onOpenAnalytics = { navController.navigate(AppRoute.Analytics.route) },
                    onOpenSignals = { navController.navigate(AppRoute.Signals.route) }
                )
            }
            composable(AppRoute.Settings.route) {
                SettingsScreen(onOpenReadiness = { navController.navigate(AppRoute.Readiness.route) })
            }
            composable(AppRoute.Readiness.route) { ReadinessScreen() }
        }
    

}
}
