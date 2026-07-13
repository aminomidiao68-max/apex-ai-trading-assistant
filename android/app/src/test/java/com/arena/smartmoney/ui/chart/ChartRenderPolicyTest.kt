package com.arena.smartmoney.ui.chart

import com.arena.smartmoney.data.model.SmcLabel
import com.arena.smartmoney.data.model.SmcZone
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChartRenderPolicyTest {
    @Test
    fun latestLiquidityLevels_deduplicatesEachKind() {
        val items = listOf(
            SmcLabel(kind = "buyside_liq", index = 1, price = 101f),
            SmcLabel(kind = "buyside_liq", index = 7, price = 107f),
            SmcLabel(kind = "sellside_liq", index = 3, price = 98f),
            SmcLabel(kind = "eqh", index = 4, price = 105f),
            SmcLabel(kind = "eqh", index = 9, price = 109f),
            SmcLabel(kind = "other", index = 10, price = 100f),
        )

        val result = ChartRenderPolicy.latestLiquidityLevels(items)

        assertEquals(listOf(3, 7, 9), result.map { it.index })
        assertEquals(1, result.count { it.kind == "buyside_liq" })
        assertEquals(1, result.count { it.kind == "eqh" })
    }

    @Test
    fun compactZoneLabels_areReadable() {
        assertEquals("Bull OB", ChartRenderPolicy.compactZoneLabel(SmcZone(kind = "OB", side = "bullish")))
        assertEquals("Bear OB", ChartRenderPolicy.compactZoneLabel(SmcZone(kind = "OB", side = "bearish")))
        assertEquals("FVG", ChartRenderPolicy.compactZoneLabel(SmcZone(kind = "FVG")))
        assertEquals("Breaker", ChartRenderPolicy.compactZoneLabel(SmcZone(kind = "BRK")))
    }

    @Test
    fun zoneLifecycle_rejectsInvalidIndexes() {
        assertTrue(
            ChartRenderPolicy.isZoneLifecycleValid(
                SmcZone(kind = "OB", index = 10, endIdx = 30), candleCount = 100
            )
        )
        assertFalse(
            ChartRenderPolicy.isZoneLifecycleValid(
                SmcZone(kind = "FVG", index = 30, endIdx = 10), candleCount = 20
            )
        )
        assertFalse(
            ChartRenderPolicy.isZoneLifecycleValid(
                SmcZone(kind = "BRK", index = 101, endIdx = 120), candleCount = 100
            )
        )
    }
}
