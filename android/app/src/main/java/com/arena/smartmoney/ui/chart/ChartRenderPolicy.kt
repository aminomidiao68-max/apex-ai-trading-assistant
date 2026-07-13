package com.arena.smartmoney.ui.chart

import com.arena.smartmoney.data.model.SmcLabel
import com.arena.smartmoney.data.model.SmcZone

/** Pure rendering policies shared by the chart and Android unit tests. */
internal object ChartRenderPolicy {
    private val liquidityKinds = listOf("buyside_liq", "sellside_liq", "eqh", "eql")

    fun latestLiquidityLevels(items: List<SmcLabel>): List<SmcLabel> {
        return liquidityKinds.mapNotNull { kind ->
            items.lastOrNull { it.kind == kind }
        }.sortedBy { it.index }
    }

    fun compactZoneLabel(zone: SmcZone): String = when (zone.kind) {
        "OB" -> if (zone.side == "bullish") "Bull OB" else "Bear OB"
        "FVG" -> "FVG"
        "iFVG" -> "iFVG"
        "BRK" -> "Breaker"
        else -> zone.kind
    }

    fun isZoneLifecycleValid(zone: SmcZone, candleCount: Int): Boolean {
        if (zone.kind == "KZ") return true
        if (candleCount <= 0 || zone.index !in 0 until candleCount) return false
        val end = if (zone.endIdx >= zone.index) zone.endIdx else candleCount - 1
        return end in zone.index until candleCount
    }
}
