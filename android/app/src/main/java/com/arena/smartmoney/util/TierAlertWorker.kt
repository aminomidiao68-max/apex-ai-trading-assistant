package com.arena.smartmoney.util

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.arena.smartmoney.data.repository.TradingRepository

/**
 * v3.31 tier alerts: periodically scans the same watchlist as the
 * "Probable Setups" module and notifies ONLY for the two highest tiers
 * (ACTIONABLE / HIGH_CONFIDENCE_WATCH). PROB_WATCH_70 stays in-app only.
 *
 * Honesty rules:
 *  - the probability shown is the model's UNCALIBRATED estimate, labeled as such;
 *  - the same symbol+tier is suppressed for 4 hours (no notification spam);
 *  - symbols that fail to fetch are skipped silently and retried next cycle.
 */
class TierAlertWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val repo = TradingRepository()
        val watchlist = listOf(
            Triple("BTCUSDT", "crypto", "1h"),
            Triple("ETHUSDT", "crypto", "1h"),
            Triple("SOLUSDT", "crypto", "1h"),
            Triple("XAUUSD", "", "1h"),
            Triple("XAGUSD", "", "1h"),
            Triple("EURUSD", "", "1h"),
            Triple("GBPUSD", "", "1h"),
            Triple("USDJPY", "", "1h"),
            Triple("GBPJPY", "", "1h"),
            Triple("USOIL", "", "1h"),
            Triple("US100", "", "1h"),
        )
        val prefs = applicationContext.getSharedPreferences("tier_alerts", Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        for ((symbol, market, interval) in watchlist) {
            try {
                val report = repo.getSmcAnalysis(
                    symbol = symbol,
                    market = market,
                    interval = interval,
                )
                val tier = report.displayTier
                if (tier != "ACTIONABLE" && tier != "HIGH_CONFIDENCE_WATCH") continue
                val key = symbol + "_" + tier
                if (now - prefs.getLong(key, 0L) < SUPPRESS_MS) continue
                prefs.edit().putLong(key, now).apply()
                val sideFa = if (report.direction == "long") "خرید (LONG)" else "فروش (SHORT)"
                val tierFa = if (tier == "ACTIONABLE") {
                    "🟢 سیگنال اکشن — همهٔ گیت‌ها پاس"
                } else {
                    "🟡 تماشای اطمینان بالا (≥۸۰٪)"
                }
                NotificationHelper.showSignalNotification(
                    applicationContext,
                    "$tierFa — $symbol",
                    "$sideFa • احتمال برد تخمینی (غیرکالیبره) ${report.estimatedWinProbability}٪ " +
                        "• گرید ${report.grade} • RR ${"%.1f".format(report.rr)}",
                    key.hashCode(),
                )
            } catch (_: Exception) {
                // offline symbol — next cycle retries
            }
        }
        return Result.success()
    }

    companion object {
        const val UNIQUE_NAME = "apex_tier_alerts"
        private const val SUPPRESS_MS = 4 * 60 * 60 * 1000L
    }
}
