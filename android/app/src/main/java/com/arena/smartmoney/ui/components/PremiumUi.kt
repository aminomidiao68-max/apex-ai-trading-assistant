package com.arena.smartmoney.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun PremiumScreenBackground(
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        Color(0xFF050B14),
                        Color(0xFF08131F),
                        Color(0xFF0C1F2D),
                        Color(0xFF050B14)
                    )
                )
            )
    ) {
        content()
    }
}

@Composable
fun PremiumGlassCard(
    modifier: Modifier = Modifier,
    borderColor: Color = Color(0x4037E6FF),
    backgroundBrush: Brush = Brush.linearGradient(
        listOf(Color(0xCC0D1724), Color(0xCC122031), Color(0xCC0D1724))
    ),
    content: @Composable ColumnScope.() -> Unit
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(backgroundBrush, RoundedCornerShape(24.dp))
            .border(1.dp, borderColor, RoundedCornerShape(24.dp))
            .padding(16.dp),
        content = content
    )
}

@Composable
fun PremiumSectionHeader(
    title: String,
    subtitle: String? = null
) {
    Column {
        Text(
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            color = Color.White,
            fontWeight = FontWeight.ExtraBold
        )
        if (!subtitle.isNullOrBlank()) {
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFFBCEEFF)
            )
        }
    }
}

@Composable
fun premiumTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedTextColor = Color.White,
    unfocusedTextColor = Color.White,
    disabledTextColor = Color(0xFFBCEEFF),
    focusedBorderColor = Color(0xFF4D8DFF),
    unfocusedBorderColor = Color(0x66BCEEFF),
    focusedLabelColor = Color(0xFF67ECFF),
    unfocusedLabelColor = Color(0x88BCEEFF),
    cursorColor = Color(0xFF67ECFF),
    focusedContainerColor = Color.Transparent,
    unfocusedContainerColor = Color.Transparent
)

fun premiumTextFieldStyle(): TextStyle = TextStyle(color = Color.White)
