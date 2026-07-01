package com.arena.smartmoney

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.arena.smartmoney.ui.TradingAiApp
import com.arena.smartmoney.ui.theme.ArenaSmartMoneyTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ArenaSmartMoneyTheme {
                TradingAiApp()
            }
        }
    }
}
