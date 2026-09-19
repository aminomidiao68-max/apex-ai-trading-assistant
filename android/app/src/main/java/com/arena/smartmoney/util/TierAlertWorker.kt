package com.arena.smartmoney.util

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.arena.smartmoney.data.repository.TradingRepository

/**
 * v3.31 tier alerts: periodically scans the AlertPrefs watchlist and notifies
 * per the user's settings (Alert Settings module). Defaults: ACTIONABLE always,
 * HIGH_CONFIDENCE_WATCH on, PROB_WATCH_70 off (in-app only).
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
        val ctx = applicationContext
        if (!AlertPrefs.alertsEnabled(ctx)) return Result.success()
        val enabledSymbols = AlertPrefs.symbols(ctx)
        val notifyHigh = AlertPrefs.notifyHighConfidence(ctx)
        val notifyProb70 = AlertPrefs.notifyProb70(ctx)
        val repo = TradingRepository()
        val prefs = ctx.getSharedPreferences("tier_alerts", Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        for ((symbol, market, interval) in AlertPrefs.watchlist) {
            if (symbol !in enabledSymbols) continue
            try {
                val report = repo.getSmcAnalysis(
                    symbol = symbol,
                    market = market,
                    interval = interval,
                )
                val tier = report.displayTier
                val shouldNotify = when (tier) {
                    "ACTIONABLE" -> true
                    "HIGH_CONFIDENCE_WATCH" -> notifyHigh
                    "PROB_WATCH_70" -> notifyProb70
                    else -> false
                }
                if (!shouldNotify) continue
                val key = symbol + "_" + tier
                if (now - prefs.getLong(key, 0L) < SUPPRESS_MS) continue
                prefs.edit().putLong(key, now).apply()
                val sideFa = if (report.direction == "long") "خرید (LONG)" else "فروش (SHORT)"
                val tierFa = when (tier) {
                    "ACTIONABLE" -> "🟢 سیگنال اکشن — همهٔ گیت‌ها پاس"
                    "HIGH_CONFIDENCE_WATCH" -> "🟡 تماشای اطمینان بالا (≥۸۰٪)"
                    else -> "🔵 ستاپ محتمل (≥۷۰٪)"
                }
                NotificationHelper.showSignalNotification(
                    ctx,
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
