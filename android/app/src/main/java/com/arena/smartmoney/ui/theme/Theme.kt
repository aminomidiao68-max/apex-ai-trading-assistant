package com.arena.smartmoney.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val DarkColors = darkColorScheme(
    primary = Blue80,
    secondary = Blue40,
    surface = CardBg,
    background = DarkBg
)

private val LightColors = lightColorScheme(
    primary = Blue40,
    secondary = Blue80
)

@Composable
fun ArenaSmartMoneyTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content
    )
}
