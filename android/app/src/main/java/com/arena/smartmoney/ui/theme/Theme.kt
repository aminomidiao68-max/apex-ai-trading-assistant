package com.arena.smartmoney.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val DarkColors = darkColorScheme(
    primary = CyanAccent,
    secondary = BlueAccent,
    tertiary = TealAccent,
    background = DarkBg,
    surface = CardBg,
    surfaceVariant = CardBgElevated,
    onBackground = SoftText,
    onSurface = SoftText
)

private val LightColors = lightColorScheme(
    primary = BlueAccent,
    secondary = CyanAccent,
    tertiary = TealAccent
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
