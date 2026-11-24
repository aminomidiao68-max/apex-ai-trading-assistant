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
            Section(
                "🤖 هوش مصنوعی",
                "زنجیرهٔ مشاورهٔ هوشمند با چند ارائه‌دهنده (OpenRouter، Groq و Cerebras به‌عنوان جایگزین) " +
                    "تحلیل متنی و خلاصهٔ شواهد را می‌سازد. هوش مصنوعی فقط مشاور است: هیچ‌وقت verdict " +
                    "هستهٔ قطعی را تغییر نمی‌دهد و هر ادعایش با دادهٔ واقعی بازار راستی‌آزمایی می‌شود. " +
                    "هستهٔ تصمیم‌گیری کاملاً deterministic و مستقل از AI است.",
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
                " داده‌های واقعی",
                "کندل‌های زندهٔ صرافی‌های واقعی، اوردرفلو واقعی (عمق، اسپرد، فاندینگ)، فوت‌پرینت و " +
                    "ایمبالانس معامله‌های بزرگ، و والیوم‌پروفایل وقتی منبع واقعی در دسترس باشد. " +
                    "هیچ دادهٔ شبیه‌سازی‌شده‌ای در گیت‌ها استفاده نمی‌شود؛ نبود دادهٔ واقعی یعنی رد شدن.",
            )
            Section(
                "🛡 فیلترها و وسواس سیستم",
                "۲۷ گیت سخت: گرید فقط A+، کانفلونس ≥۸۵، احتمال ≥۸۸، RR ≥۳٫۵، کیفیت داده ≥۹۲، بودجهٔ " +
                    "شواهد منفی صفر، استاپ پشت سویینگ ۲۰ کندلی، ورود بدون تعقیب قیمت، کندل تأیید " +
                    "انگالفینگ، کیل‌زون فقط هم‌پوشانی لندن/نیویورک ۱۲–۱۶ UTC، وتوی آخر هفته، بلک‌اوت " +
                    "خبری ۹۰/۴۵ دقیقه، و وتوی ۳۰ روزه نمادِ بازنده. هیچ سقف مصنوعی برای تعداد ستاپ " +
                    "وجود ندارد؛ انتخاب فقط بر پایه کیفیت است — ممکن است در یک روز چند ستاپ درجه‌یک " +
                    "داشته باشیم و در یک هفته هیچ. ستاپ‌هایی با احتمال برد تخمینی ۷۰–۸۰٪ به بالا در " +
                    "بخش «ستاپ‌های محتمل» به‌صورت لایه تماشا نمایش داده می‌شوند (احتمال، تخمین " +
                    "غیرکالیبرهٔ مدل است، نه وعده). " +
                    "شعار سیستم: سیگنال ندادن بهتر از سیگنال غلط است.",
            )
            Section(
                "🎯 دقت و وین‌ریت — صادقانه",
                "این برنامه عمداً کم‌سیگنال است (هدف: ۱–۲ ستاپ دقیق در هفته). وین‌ریت و expectancy فقط " +
                    "از آزمون زندهٔ رو به جلو (سایه‌پنل) گزارش می‌شود: وقتی ≥۳۰ نتیجهٔ resolve‌شده و " +
                    "≥۷ روز پوشش واقعی جمع شود، همراه بازهٔ اطمینان ۹۵٪ ویلسون. تا آن روز پاسخ صادقانه " +
                    "«شواهد ناکافی» است و هیچ عددی ساخته نمی‌شود. سقف ساختاری وین‌ریت در این سبک " +
                    "حدود ۶۰–۶۵٪ است و هر ادعای بالاتر، بازاریابی است نه آمار. وضعیت زندهٔ کوهورت فعلی " +
                    "در بخش «آزمون واقعی دقت» همین برنامه دیده می‌شود.",
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
