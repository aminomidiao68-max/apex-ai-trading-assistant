package com.arena.smartmoney.ui.analyze

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Upload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
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
fun AnalyzeScreen() {
    val isFarsi = AppLanguageState.current == "fa"
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        Text(
                            if (isFarsi) "آنالیز چارت" else "Chart Analysis",
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
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header Info Bar (Analyses: infinite, Plan: FREE, Chats: 0/8)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = if (isFarsi) "آنالیزها: ∞" else "Analyses: ∞",
                    color = TextMid,
                    fontSize = 13.sp
                )
                Text(
                    text = if (isFarsi) "طرح: رایگان" else "Plan: FREE",
                    color = TextMid,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = if (isFarsi) "چت‌ها: ۰/۸" else "Chats: 0/8",
                    color = TextMid,
                    fontSize = 13.sp
                )
            }

            // ABN Seamless Payment banner
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Idwide", color = Color.Gray, fontSize = 12.sp)
                    Text(
                        "ÅBN Seamless Payment Integration",
                        color = Color.DarkGray,
                        fontWeight = FontWeight.Bold,
                        fontSize = 12.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            // Pro Features Premium Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = CardC),
                shape = RoundedCornerShape(12.dp),
                border = BorderStroke(1.dp, Color(0xFF6B4EFF))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (isFarsi) "آزاد کردن ویژگی‌های ویژه" else "Unlock Pro Features",
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = if (isFarsi) "سناریوهای ترید خلاف روند" else "Counter-Trade Scenarios",
                        color = Color(0xFFA78BFA),
                        fontSize = 12.sp
                    )
                }
            }

            // Dashed Selection Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .border(
                        BorderStroke(2.dp, Blue),
                        shape = RoundedCornerShape(12.dp)
                    )
                    .clickable { /* Select Screenshot */ },
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterVertically,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Upload,
                        contentDescription = "Upload",
                        tint = Blue,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = if (isFarsi) "انتخاب تصویر چارت" else "Select 1 Chart Screenshot",
                        color = Blue,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            // How it works guide
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = CardC),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = if (isFarsi) "راهنمای کارکرد" else "How it Works",
                        color = Color.White,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = if (isFarsi) 
                            "۱. یک تصویر اسکرین‌شات از چارت آپلود کنید.\n۲. هوش مصنوعی روند، ساختار، مومنتوم و الگوها را آنالیز می‌کند.\n۳. قیمت ورود، ستاپ، حد ضرر و حد سودهای چندگانه را بگیرید."
                            else 
                            "1. Upload up to 1 chart timeframe screenshot.\n2. Our AI analyzes trend, structure, momentum & patterns.\n3. Get setup, order type, entry range, SL & multiple TPs.",
                        color = TextMid,
                        fontSize = 12.sp,
                        lineHeight = 18.sp
                    )
                }
            }
        }
    }
}
