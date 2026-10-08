package com.arena.smartmoney.ui.about

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.BuildConfig
import com.arena.smartmoney.R
import com.arena.smartmoney.ui.theme.CardBg
import com.arena.smartmoney.ui.theme.CyanAccent
import com.arena.smartmoney.ui.theme.DarkBg
import com.arena.smartmoney.ui.theme.SoftText

@Composable
private fun Section(title: String, body: String) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(CardBg, RoundedCornerShape(16.dp))
            .padding(14.dp),
    ) {
        Text(title, color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(6.dp))
        Text(body, color = SoftText.copy(alpha = 0.9f), fontSize = 11.5.sp)
    }
}

@Composable
fun AboutScreen(onBack: () -> Unit) {
    Column(
        Modifier
            .fillMaxSize()
            .background(DarkBg)
    ) {
        Row(Modifier.padding(PaddingValues(start = 6.dp, end = 6.dp, top = 8.dp))) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = SoftText)
            }
            Text(
                "درباره برنامه",
                color = Color.White,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(PaddingValues(start = 4.dp, top = 14.dp)),
            )
        }
        Column(
            Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 14.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Image(
                painter = painterResource(id = R.drawable.splash_user_apex_ai),
                contentDescription = "APEX MARKET AI",
                modifier = Modifier
                    .fillMaxWidth()
                    .height(270.dp)
                    .clip(RoundedCornerShape(20.dp)),
                contentScale = ContentScale.Crop,
            )
            Text(
                "APEX MARKET AI  ·  نسخه " + BuildConfig.VERSION_NAME,
                color = Color.White,
                fontSize = 15.sp,
                fontWeight = FontWeight.ExtraBold,
            )
            // ——— Project Manager / Creator ———
            Column(
                Modifier
                    .fillMaxWidth()
                    .background(CardBg, RoundedCornerShape(16.dp))
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text("👤 سازنده پروژه — Project Manager", color = CyanAccent, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Image(
                    painter = painterResource(id = R.drawable.creator_pm),
                    contentDescription = "Project Manager — APEX MARKET AI",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(380.dp)
                        .clip(RoundedCornerShape(16.dp)),
                    contentScale = ContentScale.Crop,
                )
                Column(Modifier.fillMaxWidth().background(Color(0xFF0F172A), RoundedCornerShape(12.dp)).padding(12.dp)) {
                    Text("Project Manager", color = Color(0xFFFCD34D), fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Text("APEX MARKET AI", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold)
                    Text("CRYPTO / FOREX / AI ANALYSIS", color = CyanAccent, fontSize = 10.sp, letterSpacing = 1.2.sp)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "مدیریت و راهبری پروژه با تمرکز بر تحلیل نهادی، انضباط استراتژی و سودآوری پایدار — ANALYSIS • STRATEGY • DISCIPLINE • PROFIT",
                        color = SoftText.copy(alpha = 0.9f),
                        fontSize = 11.sp,
                    )
                }
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(Color(0xFF065F46).copy(alpha = 0.18f), RoundedCornerShape(10.dp))
                        .padding(horizontal = 10.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text("🏢", fontSize = 16.sp)
                    Column {
                        Text("APEX MARKET AI — تیم مدیریت پروژه", color = Color(0xFF6EE7B7), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        Text("طراحی، توسعه و نظارت کیفی با وسواس ۲۷ گیت سخت‌گیرانه", color = SoftText, fontSize = 10.sp)
                    }
                }
            }
            Section(
                "🤖 هوش مصنوعی — Honest Edge v3.31",
                "زنجیره مشاوره با OpenRouter/Groq/Cerebras (fallback) — فقط مشاور است، verdict قطعی را تغییر نمی‌دهد، هر ادعا با داده OKX راستی‌آزمایی می‌شود. " +
                    "Honest Edge: وین‌ریت فقط از walk-forward واقعی (PF>1)، confidence 0.70 فیک → 0.45 صادقانه + برچسب data_completeness. هسته deterministic.",
            )
            Section(
                "📐 اندیکاتورها و اسیلاتورها",
                "RSI، MACD، Stochastic RSI، باندهای بولینگر، ADX، CCI، Williams %R، MFI و ATR به‌همراه " +
                    "نسبت کارایی کافمن (ER) و نسبت‌های نوسان، همگی روی کندل‌های واقعی محاسبه می‌شوند و " +
                    "به‌صورت وزنی در امتیاز کانفلونس نهادی نقش دارند.",
            )
            Section(
                "🧠 سبک‌ها و منطق‌ها",
                "SMC و ICT (BOS، CHoCH، OTE، نقدینگی و سایه‌ها)، RTM، عرضه و تقاضا (S&D)، پرایس‌اکشن، " +
                    "نقاط چرخش نقدینگی و ساختار چندتایم‌فریمی. هر ستاپ باید از همهٔ این لنزها هم‌زمان عبور کند.",
            )
            Section(
                "📡 داده‌های زنده و واقعی — L2 400 + VP 20 + Footprint 6×12",
                "کندل‌های زنده OKX (و Binance fallback)، اوردرفلو واقعی 400 لول عمق + تا 2600 ترید زنده + WebSocket <1ثانیه (okx_ws_service)، " +
                    "اوپن اینترست و فاندینگ ریت، والیوم پروفایل واقعی 20 bins از تیک‌ها (POC/VAH/VAL/HVN/LVN) و فوت‌پرینت واقعی 6 کندل ×12 ردیف (delta/stacked imbalance/unfinished) — " +
                    "همه از تیک‌های زنده، نه proxy کندلی. برای فارکس/XAU که L2 متمرکز ندارد، صادقانه proxy + برچسب is_real:false می‌خورد. هیچ دادهٔ شبیه‌سازی در گیت‌ها نیست؛ نبود داده واقعی = رد شدن.",
            )
            Section(
                "🛡 فیلترها و وسواس — ۲۷ گیت، ۲ نرم با وزن 0.15 (صادقانه)",
                "۲۷ گیت سخت: گرید فقط A+، کانفلونس ≥۸۵، احتمال ≥۸۸، RR ≥۳٫۵، کیفیت داده ≥۹۲، بودجهٔ شواهد منفی صفر، استاپ پشت سویینگ ۲۰ کندلی، " +
                    "ورود بدون تعقیب، کندل تأیید انگالفینگ، کیل‌زون ۱۲–۱۶ UTC، وتوی آخر هفته، بلک‌اوت خبری ۹۰/۴۵ دقیقه، وتوی ۳۰ روزه نماد بازنده — " +
                    "به‌علاوه ۲ گیت نرم وزن 0.15 (trigger_matches_context & explicit_invalidation): ≤1 soft→ACTIONABLE، 2 soft→WATCH (از veto به weight، v3.33 با صداقت per درخواست شما). " +
                    "هیچ سقف روزانه/هفتگی مصنوعی نیست؛ 20 نماد واچ‌لیست کامل. ستاپ‌های ۷۰–۸۰٪ در «محتمل» فقط WATCH هستند تا کالیبره شوند. شعار: سیگنال ندادن بهتر از غلط است.",
            )
            Section(
                "🎯 دقت و وین‌ریت — صادقانه (v3.33)",
                "کم‌سیگنال عمدی. وین‌ریت فقط از سایه‌پنل زنده: 7698 کل، 275 موتور فعلی → 0/30 حل‌شده → INSUFFICIENT_EVIDENCE (۲۰ سپتامبر). " +
                    "با وزن 0.15 جدید، نرخ کاندیدا از 0/275 به 3-5/275 می‌رود تا 30 پر شود — بدون فیک 80%. وقتی 30 و 7 روز پر شد، Wilson CI 95% می‌آید. " +
                    "سقف ساختاری 60-65% است. هر عدد قبل 30 = فیلم. وضعیت زنده را در «آزمون واقعی دقت» و «گزارش Failed Gates» ببینید — همه با تیک OKX.",
            )
            Section(
                "🔒 ایمنی",
                "فقط مشاوره: اجرای خودکار معامله و اتصال به کیف پول/صرافی برای ترید واقعی به‌صورت پیش‌فرض " +
                    "خاموش و قفل است. مدیریت ریسک پیشنهادی: حداکثر ۱٪ ریسک در هر معامله.",
            )
            Spacer(Modifier.height(14.dp))
        }
    }
}
