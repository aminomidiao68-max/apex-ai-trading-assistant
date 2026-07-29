package com.arena.smartmoney.ui.analyze

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Upload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.network.AppConfig
import com.arena.smartmoney.ui.i18n.AppLanguageState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

private val BgDark = Color(0xFF0B0F14)
private val CardC = Color(0xFF161C25)
private val TextHi = Color(0xFFF2F4F7)
private val TextMid = Color(0xFF9AA3B2)
private val Blue = Color(0xFF00A2FF)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalyzeScreen() {
    val isFarsi = AppLanguageState.current == "fa"
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    
    var selectedImageUri by remember { mutableStateOf<Uri?>(null) }
    var analysisResult by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }

    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        selectedImageUri = uri
        if (uri != null) {
            loading = true
            analysisResult = null
            coroutineScope.launch {
                try {
                    val compressedBytes = withContext(Dispatchers.IO) {
                        context.contentResolver.openInputStream(uri)?.use { stream ->
                            val rawBytes = stream.readBytes()
                            val bitmap = BitmapFactory.decodeByteArray(rawBytes, 0, rawBytes.size)
                            if (bitmap != null) {
                                // Downscale image to max 1024px to prevent Groq 2048px limit 400 Bad Request
                                val maxDimension = 1024
                                val originalWidth = bitmap.width
                                val originalHeight = bitmap.height
                                val scaledBitmap = if (originalWidth > maxDimension || originalHeight > maxDimension) {
                                    val aspectRatio = originalWidth.toFloat() / originalHeight.toFloat()
                                    val (newWidth, newHeight) = if (originalWidth > originalHeight) {
                                        maxDimension to (maxDimension / aspectRatio).toInt()
                                    } else {
                                        (maxDimension * aspectRatio).toInt() to maxDimension
                                    }
                                    Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true)
                                } else {
                                    bitmap
                                }
                                
                                val outputStream = ByteArrayOutputStream()
                                scaledBitmap.compress(Bitmap.CompressFormat.JPEG, 70, outputStream)
                                outputStream.toByteArray()
                            } else {
                                null
                            }
                        }
                    }
                    if (compressedBytes != null) {
                        val resultText = uploadAndAnalyzeImage(compressedBytes)
                        analysisResult = resultText
                    } else {
                        analysisResult = if (isFarsi) "❌ خطا در فشرده‌سازی فایل تصویر." else "❌ Error compressing image file."
                    }
                } catch (e: Exception) {
                    analysisResult = "❌ Error: ${e.message}"
                } finally {
                    loading = false
                }
            }
        }
    }
    
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
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
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
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
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

            // Dashed Selection Box (Launch Image Picker)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .border(
                        BorderStroke(2.dp, Blue),
                        shape = RoundedCornerShape(12.dp)
                    )
                    .clickable { imagePickerLauncher.launch("image/*") },
                contentAlignment = Alignment.Center
            ) {
                if (loading) {
                    CircularProgressIndicator(color = Blue)
                } else {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
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
            }

            // Display Real AI Analysis Result
            analysisResult?.let { result ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardC),
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(1.dp, Blue.copy(alpha = 0.5f))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = if (isFarsi) "✨ تحلیل هوش مصنوعی واقعی چارت شما:" else "✨ Real AI Chart Analysis:",
                            color = Blue,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = result,
                            color = Color.White,
                            fontSize = 13.sp,
                            lineHeight = 20.sp
                        )
                    }
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

private suspend fun uploadAndAnalyzeImage(bytes: ByteArray): String = withContext(Dispatchers.IO) {
    try {
        // Enforce high-res client timeout of 60 seconds for slow networks / VPNs
        val client = OkHttpClient.Builder()
            .connectTimeout(60, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()

        val mediaType = "image/jpeg".toMediaTypeOrNull()
        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file", "chart.jpg",
                bytes.toRequestBody(mediaType)
            )
            .build()

        val request = Request.Builder()
            .url(AppConfig.apiBaseUrl + "api/v1/analysis/vision")
            .post(requestBody)
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                return@withContext "❌ API Error: HTTP ${response.code}"
            }
            val bodyString = response.body?.string() ?: ""
            val json = JSONObject(bodyString)
            return@withContext json.optString("analysis", "❌ Failed to parse response.")
        }
    } catch (e: Exception) {
        return@withContext "❌ Error connecting to server: ${e.message}"
    }
}
