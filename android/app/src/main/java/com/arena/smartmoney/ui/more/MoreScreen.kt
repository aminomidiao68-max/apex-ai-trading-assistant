package com.arena.smartmoney.ui.more

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.network.AppLanguageState

private val BgDark = Color(0xFF0B0F14)
private val CardC = Color(0xFF161C25)
private val TextHi = Color(0xFFF2F4F7)
private val TextMid = Color(0xFF9AA3B2)
private val Blue = Color(0xFF00A2FF)
private val Gold = Color(0xFFFFA200)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MoreScreen(
    onNavigate: (String) -> Unit
) {
    val isFarsi = AppLanguageState.current == "fa"

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        Text(
                            if (isFarsi) "بیشتر" else "More",
                            color = TextHi,
                            fontWeight = FontWeight.Bold,
                            fontSize = 20.sp
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BgDark)
            )
        },
        containerColor = BgDark
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // More Subtitle
            item {
                Text(
                    text = if (isFarsi) "دسترسی به تمام ابزارها در یکجا" else "Access all your tools in one place",
                    color = TextMid,
                    fontSize = 14.sp
                )
            }

            // Tools Section Header
            item {
                Text(
                    text = if (isFarsi) "ابزارها" else "TOOLS",
                    color = TextMid,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp
                )
            }

            // Tool item: Analysis History
            item {
                MoreItemRow(
                    title = if (isFarsi) "تاریخچه آنالیزها" else "Analysis History",
                    subtitle = if (isFarsi) "مشاهده سیگنال‌ها و آنالیزهای چارت گذشته" else "View past chart analyses and signals",
                    icon = Icons.Default.History,
                    iconColor = Blue,
                    onClick = { onNavigate("analytics") }
                )
            }

            // Tool item: Price Alerts (Repurposed as System Readiness & Audit Drills)
            item {
                MoreItemRow(
                    title = if (isFarsi) "ممیزی آمادگی و راستی‌آزمایی سیستم" else "System Readiness & Audit Drills",
                    subtitle = if (isFarsi) "پایش زنده اتصال دیتابیس، امنیت ترافیک، لایه مارجین صرافی و هوش مصنوعی" else "Live monitor of database, security, margin gates and AI providers",
                    icon = Icons.Default.VerifiedUser,
                    iconColor = Gold,
                    onClick = { onNavigate("readiness") }
                )
            }

            // Tool item: Live Prices
            item {
                MoreItemRow(
                    title = if (isFarsi) "قیمت‌های زنده" else "Live Prices",
                    subtitle = if (isFarsi) "جریان زنده قیمت‌های فارکس و کریپتو (روشن)" else "Stream real-time forex & crypto prices",
                    icon = Icons.Default.ShowChart,
                    iconColor = Color(0xFF22C55E),
                    badge = if (isFarsi) "خاموش" else "Off",
                    onClick = { onNavigate("chart") }
                )
            }

            // Account Section Header
            item {
                Text(
                    text = if (isFarsi) "تنظیمات حساب" else "ACCOUNT",
                    color = TextMid,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp
                )
            }

            // Account item: Settings
            item {
                MoreItemRow(
                    title = if (isFarsi) "تنظیمات" else "Settings",
                    subtitle = if (isFarsi) "اشتراک، زبان، تنظیمات حریم خصوصی" else "Subscription, language, preferences & more",
                    icon = Icons.Default.Settings,
                    iconColor = TextMid,
                    onClick = { onNavigate("settings") }
                )
            }

            // Broker, Risk, Journal, Backtest Links
            item {
                MoreItemRow(
                    title = if (isFarsi) "ماشین حساب ریسک" else "Risk Calculator",
                    subtitle = if (isFarsi) "تعیین خودکار حجم و مارجین پوزیشن" else "Determine position sizing and margin",
                    icon = Icons.Default.Calculate,
                    iconColor = Blue,
                    onClick = { onNavigate("risk") }
                )
            }
            item {
                MoreItemRow(
                    title = if (isFarsi) "تنظیمات بروکر" else "Broker Integration",
                    subtitle = if (isFarsi) "اتصال کلیدهای بایننس و حسابهای دمو" else "Connect exchange API keys and accounts",
                    icon = Icons.Default.AccountBalance,
                    iconColor = Blue,
                    onClick = { onNavigate("broker") }
                )
            }

            // Community Section Header
            item {
                Text(
                    text = if (isFarsi) "جامعه کاربری" else "COMMUNITY",
                    color = TextMid,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp
                )
            }

            // WhatsApp link
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { /* Join WhatsApp */ },
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF155E37))
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Group, contentDescription = "WhatsApp", tint = Color.White)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            if (isFarsi) "عضویت در کانال واتساپ" else "Join WhatsApp Community",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MoreItemRow(
    title: String,
    subtitle: String,
    icon: ImageVector,
    iconColor: Color,
    badge: String? = null,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = CardC)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = title,
                tint = iconColor,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    if (badge != null) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(Color(0xFFEF4444).copy(alpha = 0.2f))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text(badge, color = Color(0xFFEF4444), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
                Spacer(modifier = Modifier.height(2.dp))
                Text(subtitle, color = TextMid, fontSize = 11.sp)
            }
            Spacer(modifier = Modifier.width(8.dp))
            Icon(Icons.Default.ChevronRight, contentDescription = "Open", tint = TextMid)
        }
    }
}
