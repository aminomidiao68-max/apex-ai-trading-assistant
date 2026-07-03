package com.arena.smartmoney

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.arena.smartmoney.ui.theme.ArenaSmartMoneyTheme
import kotlinx.coroutines.delay

class SplashActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ArenaSmartMoneyTheme {
                SplashContent {
                    startActivity(Intent(this, MainActivity::class.java))
                    finish()
                }
            }
        }
    }
}

@Composable
private fun SplashContent(onFinish: () -> Unit) {
    LaunchedEffect(Unit) {
        delay(2400)
        onFinish()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        Color(0xFF050B14),
                        Color(0xFF091626),
                        Color(0xFF0C2232),
                        Color(0xFF050B14)
                    )
                )
            )
            .padding(24.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Column(
                modifier = Modifier.padding(top = 28.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Box(
                    modifier = Modifier
                        .shadow(22.dp, RoundedCornerShape(30.dp))
                        .background(
                            Brush.linearGradient(
                                listOf(Color(0xFF0B1525), Color(0xFF11283A), Color(0xFF0B1525))
                            ),
                            RoundedCornerShape(30.dp)
                        )
                        .border(1.dp, Color(0x6637E6FF), RoundedCornerShape(30.dp))
                        .padding(22.dp)
                ) {
                    Image(
                        painter = painterResource(id = R.drawable.ic_apex_ai_logo),
                        contentDescription = "APEX AI Logo",
                        modifier = Modifier.size(110.dp)
                    )
                }

                Text(
                    text = "APEX AI PREMIUM",
                    style = MaterialTheme.typography.headlineMedium,
                    color = Color(0xFF67ECFF),
                    fontWeight = FontWeight.ExtraBold
                )
                Text(
                    text = "Neon AI Trading Experience",
                    style = MaterialTheme.typography.titleMedium,
                    color = Color(0xFFE7F9FF)
                )
            }

            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                SplashMetricRow()

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xCC101826), RoundedCornerShape(24.dp))
                        .border(1.dp, Color(0x5549E8FF), RoundedCornerShape(24.dp))
                        .padding(vertical = 18.dp, horizontal = 20.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "Created by",
                            color = Color.White,
                            style = MaterialTheme.typography.titleSmall
                        )
                        Text(
                            text = "Amin omidi",
                            color = Color(0xFF67ECFF),
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SplashMetricRow() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        SplashMetricCard("AI", "Live")
        SplashMetricCard("TP1", "TP2/TP3")
        SplashMetricCard("FA/EN", "Bilingual")
    }
}

@Composable
private fun SplashMetricCard(title: String, value: String) {
    Box(
        modifier = Modifier
            .background(Color(0xCC0D1724), RoundedCornerShape(20.dp))
            .border(1.dp, Color(0x4037E6FF), RoundedCornerShape(20.dp))
            .padding(vertical = 14.dp, horizontal = 14.dp)
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(title, color = Color(0xFF67ECFF), fontWeight = FontWeight.Bold)
            Text(value, color = Color.White, style = MaterialTheme.typography.labelLarge)
        }
    }
}
