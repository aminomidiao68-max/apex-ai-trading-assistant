package com.arena.smartmoney.data.network

import com.arena.smartmoney.data.model.AnalyticsReportDto
import com.arena.smartmoney.data.model.NewsBrief
import com.arena.smartmoney.data.model.SmcReport
import com.arena.smartmoney.data.model.AnalyticsSummaryDto
import com.arena.smartmoney.data.model.AuthLoginRequestDto
import com.arena.smartmoney.data.model.AuthResponseDto
import com.arena.smartmoney.data.model.AuthRegisterRequestDto
import com.arena.smartmoney.data.model.AuthUserDto
import com.arena.smartmoney.data.model.BacktestRunRequestDto
import com.arena.smartmoney.data.model.BinanceFuturesOrderRequestDto
import com.arena.smartmoney.data.model.BybitOrderRequestDto
import com.arena.smartmoney.data.model.CTraderOrderRequestDto
import com.arena.smartmoney.data.model.BacktestSweepRequestDto
import com.arena.smartmoney.data.model.BacktestSweepSummaryDto
import com.arena.smartmoney.data.model.WalkForwardRequestDto
import com.arena.smartmoney.data.model.WalkForwardSummaryDto
import com.arena.smartmoney.data.model.BacktestSummaryDto
import com.arena.smartmoney.data.model.CandlesResponse
import com.arena.smartmoney.data.model.DeviceTokenItemDto
import com.arena.smartmoney.data.model.ExecutionActionResponseDto
import com.arena.smartmoney.data.model.DeviceTokenRegisterRequestDto
import com.arena.smartmoney.data.model.ExecutionCapabilitiesResponse
import com.arena.smartmoney.data.model.ExecutionPreviewRequestDto
import com.arena.smartmoney.data.model.ExecutionPreviewResponseDto
import com.arena.smartmoney.data.model.ExecutionStatusResponse
import com.arena.smartmoney.data.model.LiveSignalScanRequestDto
import com.arena.smartmoney.data.model.MarketOverviewResponse
import com.arena.smartmoney.data.model.MessageResponseDto
import com.arena.smartmoney.data.model.NotificationDispatchResultDto
import com.arena.smartmoney.data.model.Mt5OrderRequestDto
import com.arena.smartmoney.data.model.NotificationTestRequestDto
import com.arena.smartmoney.data.model.OandaOrderRequestDto
import com.arena.smartmoney.data.model.RiskPlanRequestDto
import com.arena.smartmoney.data.model.RiskPlanResponse
import com.arena.smartmoney.data.model.SessionResponse
import com.arena.smartmoney.data.model.SystemReadinessDto
import com.arena.smartmoney.data.model.SignalHistoryItemDto
import com.arena.smartmoney.data.model.SignalHistoryResponse
import com.arena.smartmoney.data.model.TradeJournalCloseRequestDto
import com.arena.smartmoney.data.model.TradeJournalCreateRequestDto
import com.arena.smartmoney.data.model.TradeJournalItemDto
import com.arena.smartmoney.data.model.TradeJournalStatsDto
import com.arena.smartmoney.data.model.TradesResponse
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface TradingApiService {
    @POST("api/v1/auth/register")
    suspend fun register(@Body request: AuthRegisterRequestDto): AuthResponseDto

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: AuthLoginRequestDto): AuthResponseDto

    @GET("api/v1/auth/me")
    suspend fun getMe(@Header("Authorization") authorization: String): AuthUserDto

    @POST("api/v1/auth/logout")
    suspend fun logout(@Header("Authorization") authorization: String): MessageResponseDto

    @POST("api/v1/notifications/register-device")
    suspend fun registerDevice(
        @Header("Authorization") authorization: String,
        @Body request: DeviceTokenRegisterRequestDto
    ): DeviceTokenItemDto

    @POST("api/v1/notifications/test")
    suspend fun sendTestNotification(
        @Header("Authorization") authorization: String,
        @Body request: NotificationTestRequestDto
    ): NotificationDispatchResultDto

    @GET("api/v1/sessions/current")
    suspend fun getCurrentSession(): SessionResponse

    @GET("api/v1/system/readiness")
    suspend fun getSystemReadiness(): SystemReadinessDto

    @GET("api/v1/analytics/summary")
    suspend fun getAnalyticsSummary(): AnalyticsSummaryDto

    @GET("api/v1/analytics/report")
    suspend fun getAnalyticsReport(): AnalyticsReportDto

    @GET("api/v1/market/overview")
    suspend fun getMarketOverview(@Query("symbols") symbols: String): MarketOverviewResponse

    @GET("api/v1/market/candles")
    suspend fun getCandles(
        @Query("symbol") symbol: String,
        @Query("market") market: String,
        @Query("interval") interval: String,
        @Query("limit") limit: Int
    ): CandlesResponse

    @GET("api/v1/execution/status")
    suspend fun getExecutionStatus(): ExecutionStatusResponse

    @GET("api/v1/execution/capabilities")
    suspend fun getExecutionCapabilities(): ExecutionCapabilitiesResponse

    @POST("api/v1/execution/preview")
    suspend fun previewExecution(@Body request: ExecutionPreviewRequestDto): ExecutionPreviewResponseDto

    @POST("api/v1/execution/binance/order")
    suspend fun placeBinanceOrder(@Body request: BinanceFuturesOrderRequestDto): ExecutionActionResponseDto

    @POST("api/v1/execution/bybit/order")
    suspend fun placeBybitOrder(@Body request: BybitOrderRequestDto): ExecutionActionResponseDto

    @POST("api/v1/execution/oanda/order")
    suspend fun placeOandaOrder(@Body request: OandaOrderRequestDto): ExecutionActionResponseDto

    @POST("api/v1/execution/mt5/order")
    suspend fun placeMt5Order(@Body request: Mt5OrderRequestDto): ExecutionActionResponseDto

    @POST("api/v1/execution/ctrader/order")
    suspend fun placeCTraderOrder(@Body request: CTraderOrderRequestDto): ExecutionActionResponseDto

    @GET("api/v1/signals/history")
    suspend fun getSignalHistory(@Query("limit") limit: Int): SignalHistoryResponse

    @POST("api/v1/signals/live-scan")
    suspend fun liveScanSignal(@Body request: LiveSignalScanRequestDto): SignalHistoryItemDto

    @POST("api/v1/backtest/run")
    suspend fun runBacktest(@Body request: BacktestRunRequestDto): BacktestSummaryDto

    @POST("api/v1/backtest/sweep")
    suspend fun runBacktestSweep(@Body request: BacktestSweepRequestDto): BacktestSweepSummaryDto

    @POST("api/v1/backtest/walk-forward")
    suspend fun runWalkForward(@Body request: WalkForwardRequestDto): WalkForwardSummaryDto

    @POST("api/v1/trades")
    suspend fun createTrade(@Body request: TradeJournalCreateRequestDto): TradeJournalItemDto

    @GET("api/v1/trades")
    suspend fun getTrades(@Query("limit") limit: Int): TradesResponse

    @GET("api/v1/trades/stats")
    suspend fun getTradeStats(): TradeJournalStatsDto

    @POST("api/v1/trades/{tradeId}/close")
    suspend fun closeTrade(
        @Path("tradeId") tradeId: Int,
        @Body request: TradeJournalCloseRequestDto
    ): TradeJournalItemDto

    @POST("api/v1/risk/plan")
    suspend fun calculateRisk(@Body request: RiskPlanRequestDto): RiskPlanResponse

    companion object {
        fun create(baseUrl: String = AppConfig.apiBaseUrl): TradingApiService {
            val logger = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            val client = OkHttpClient.Builder()
                .addInterceptor(logger)
                .build()

            return Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(TradingApiService::class.java)
        }
    }

    @GET("api/v1/news/brief")
    suspend fun getNewsBrief(): NewsBrief
    @GET("api/v1/analysis/smc")
    suspend fun getSmcAnalysis(
        @Query("symbol") symbol: String = "XAUUSD",
        @Query("market") market: String = "forex",
        @Query("interval") interval: String = "15min",
        @Query("limit") limit: Int = 220
    ): SmcReport
}
