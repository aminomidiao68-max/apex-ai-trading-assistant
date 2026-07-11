package com.arena.smartmoney.data.repository
import com.arena.smartmoney.data.model.NewsBrief
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.model.SmcLevel
import com.arena.smartmoney.data.model.SmcZone
import com.arena.smartmoney.data.model.SmcEvent
import com.arena.smartmoney.data.model.SmcLabel
import com.arena.smartmoney.data.model.SmcLine
import com.arena.smartmoney.data.model.SmcOverlay
import com.arena.smartmoney.data.model.NewsAdjustment

import com.arena.smartmoney.data.model.AuthLoginRequestDto
import com.arena.smartmoney.data.model.AuthRegisterRequestDto
import com.arena.smartmoney.data.model.BacktestRunRequestDto
import com.arena.smartmoney.data.model.BinanceFuturesOrderRequestDto
import com.arena.smartmoney.data.model.BybitOrderRequestDto
import com.arena.smartmoney.data.model.CTraderOrderRequestDto
import com.arena.smartmoney.data.model.BacktestSweepRequestDto
import com.arena.smartmoney.data.model.WalkForwardRequestDto
import com.arena.smartmoney.data.model.DeviceTokenRegisterRequestDto
import com.arena.smartmoney.data.model.ExecutionPreviewRequestDto
import com.arena.smartmoney.data.model.Mt5OrderRequestDto
import com.arena.smartmoney.data.model.OandaOrderRequestDto
import com.arena.smartmoney.data.model.LiveSignalScanRequestDto
import com.arena.smartmoney.data.model.NotificationTestRequestDto
import com.arena.smartmoney.data.model.RiskPlanRequestDto
import com.arena.smartmoney.data.model.TradeJournalCloseRequestDto
import com.arena.smartmoney.data.model.TradeJournalCreateRequestDto
import com.arena.smartmoney.data.network.TradingApiService

class TradingRepository(
    private val api: TradingApiService = TradingApiService.create()
) {
    suspend fun register(name: String, email: String, password: String) =
        api.register(AuthRegisterRequestDto(name = name, email = email, password = password))

    suspend fun login(email: String, password: String) =
        api.login(AuthLoginRequestDto(email = email, password = password))

    suspend fun getMe(authorization: String) = api.getMe(authorization)

    suspend fun logout(authorization: String) = api.logout(authorization)

    suspend fun registerDeviceToken(authorization: String, token: String, deviceName: String? = null) =
        api.registerDevice(
            authorization = authorization,
            request = DeviceTokenRegisterRequestDto(token = token, device_name = deviceName)
        )

    suspend fun sendTestNotification(authorization: String, title: String, body: String) =
        api.sendTestNotification(
            authorization = authorization,
            request = NotificationTestRequestDto(title = title, body = body)
        )

    suspend fun getCurrentSession() = api.getCurrentSession()

    suspend fun getSystemReadiness() = api.getSystemReadiness()

    suspend fun getAnalyticsSummary() = api.getAnalyticsSummary()

    suspend fun getAnalyticsReport() = api.getAnalyticsReport()

    suspend fun getMarketOverview(symbols: String) = api.getMarketOverview(symbols)

    suspend fun getCandles(symbol: String, market: String, interval: String, limit: Int = 80) =
        api.getCandles(symbol = symbol, market = market, interval = interval, limit = limit)

    suspend fun getExecutionStatus() = api.getExecutionStatus()

    suspend fun getExecutionCapabilities() = api.getExecutionCapabilities()

    suspend fun previewExecution(connector: String, symbol: String, side: String, quantity: Double, signalScore: Double, riskApproved: Boolean) =
        api.previewExecution(
            ExecutionPreviewRequestDto(
                connector = connector,
                symbol = symbol,
                side = side,
                quantity = quantity,
                signal_score = signalScore,
                risk_approved = riskApproved
            )
        )

    suspend fun placeBinanceOrder(request: BinanceFuturesOrderRequestDto) = api.placeBinanceOrder(request)

    suspend fun placeBybitOrder(request: BybitOrderRequestDto) = api.placeBybitOrder(request)

    suspend fun placeOandaOrder(request: OandaOrderRequestDto) = api.placeOandaOrder(request)

    suspend fun placeMt5Order(request: Mt5OrderRequestDto) = api.placeMt5Order(request)

    suspend fun placeCTraderOrder(request: CTraderOrderRequestDto) = api.placeCTraderOrder(request)

    suspend fun getSignalHistory(limit: Int = 30) = api.getSignalHistory(limit)

    suspend fun liveScanSignal(request: LiveSignalScanRequestDto) = api.liveScanSignal(request)

    suspend fun runBacktest(request: BacktestRunRequestDto) = api.runBacktest(request)

    suspend fun runBacktestSweep(request: BacktestSweepRequestDto) = api.runBacktestSweep(request)

    suspend fun runWalkForward(request: WalkForwardRequestDto) = api.runWalkForward(request)

    suspend fun createTrade(request: TradeJournalCreateRequestDto) = api.createTrade(request)

    suspend fun getTrades(limit: Int = 50) = api.getTrades(limit)

    suspend fun getTradeStats() = api.getTradeStats()

    suspend fun closeTrade(tradeId: Int, request: TradeJournalCloseRequestDto) = api.closeTrade(tradeId, request)

    suspend fun calculateRisk(request: RiskPlanRequestDto) = api.calculateRisk(request)



    suspend fun getNewsBrief(): NewsBrief {
        return try {
            api.getNewsBrief()
        } catch (t: Throwable) {
            NewsBrief(
                finnhub_configured = false,
                adjustment = NewsAdjustment(
                    note = "سرویس اخبار در دسترس نیست. اتصال اینترنت یا بک‌اند را بررسی کنید."
                )
            )
        }
    }

}

    suspend fun getSmcAnalysis(symbol: String = "XAUUSD", market: String = "forex", interval: String = "15min", limit: Int = 220): SmcReport {
        return try { api.getSmcAnalysis(symbol, market, interval, limit) }
        catch (e: Exception) {
            SmcReport(
                symbol = symbol, timeframe = interval, note = "خطا در بارگذاری تحلیل: ${e.message}", status = "error"
            )
        }
}
