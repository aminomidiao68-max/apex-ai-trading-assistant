package com.arena.smartmoney.ui.aichat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.arena.smartmoney.data.network.AppConfig
import com.arena.smartmoney.ui.i18n.AppLanguageState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

private val BgDark = Color(0xFF0B0F14)
private val CardC = Color(0xFF161C25)
private val TextHi = Color(0xFFF2F4F7)
private val TextMid = Color(0xFF9AA3B2)
private val Blue = Color(0xFF00A2FF)

data class ChatMessage(val text: String, val isUser: Boolean)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AIChatScreen() {
    val isFarsi = AppLanguageState.current == "fa"
    val coroutineScope = rememberCoroutineScope()
    var textState by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    
    val messages = remember {
        mutableStateListOf(
            ChatMessage(
                text = if (isFarsi) "سلام! من دستیار معاملاتی هوشمند شما هستم. در مورد ستاپ‌ها، ریسک، یا سطوح چارت بپرسید."
                       else "Hi! I'm your pro trading assistant. Ask me about setups, risk, or levels.",
                isUser = false
            )
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        Text(
                            if (isFarsi) "چت هوش مصنوعی" else "AI Chat",
                            color = TextHi,
                            fontWeight = FontWeight.Bold,
                            fontSize = 20.sp
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BgDark)
            )
        },
        bottomBar = {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(BgDark)
                    .padding(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextField(
                    value = textState,
                    onValueChange = { textState = it },
                    enabled = !sending,
                    placeholder = {
                        Text(
                            if (isFarsi) "یک سوال بپرسید..." else "Ask a question...",
                            color = TextMid
                        )
                    },
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = CardC,
                        unfocusedContainerColor = CardC,
                        focusedTextColor = TextHi,
                        unfocusedTextColor = TextHi,
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent
                    ),
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(24.dp))
                )
                Spacer(modifier = Modifier.width(8.dp))
                IconButton(
                    onClick = {
                        val query = textState.trim()
                        if (query.isNotBlank() && !sending) {
                            messages.add(ChatMessage(query, isUser = true))
                            textState = ""
                            sending = true
                            coroutineScope.launch {
                                try {
                                    val responseText = queryRealAIChatAssistant(query)
                                    messages.add(ChatMessage(responseText, isUser = false))
                                } catch (e: Exception) {
                                    messages.add(ChatMessage("❌ Error: ${e.message}", isUser = false))
                                } finally {
                                    sending = false
                                }
                            }
                        }
                    },
                    modifier = Modifier
                        .background(Blue, shape = RoundedCornerShape(50))
                        .size(48.dp)
                ) {
                    if (sending) {
                        CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                    } else {
                        Icon(
                            imageVector = Icons.Default.Send,
                            contentDescription = "Send",
                            tint = Color.White
                        )
                    }
                }
            }
        },
        containerColor = BgDark
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(messages) { msg ->
                val alignment = if (msg.isUser) Alignment.End else Alignment.Start
                val bg = if (msg.isUser) Blue else CardC
                val textCol = Color.White
                
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = alignment
                ) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(bg)
                            .padding(12.dp)
                            .widthIn(max = 280.dp)
                    ) {
                        Text(msg.text, color = textCol, fontSize = 14.sp)
                    }
                }
            }
        }
    }
}

private suspend fun queryRealAIChatAssistant(message: String): String = withContext(Dispatchers.IO) {
    try {
        // Enforce high-res client timeout of 60 seconds for slow networks / VPNs
        val client = OkHttpClient.Builder()
            .connectTimeout(60, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()

        val mediaType = "application/json".toMediaTypeOrNull()
        val jsonPayload = JSONObject().apply {
            put("message", message)
        }.toString()

        val requestBody = jsonPayload.toRequestBody(mediaType)
        val request = Request.Builder()
            .url(AppConfig.apiBaseUrl + "api/v1/aichat")
            .post(requestBody)
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                return@withContext "❌ API Error: HTTP ${response.code}"
            }
            val bodyString = response.body?.string() ?: ""
            val json = JSONObject(bodyString)
            return@withContext json.optString("reply", "❌ Failed to parse response.")
        }
    } catch (e: Exception) {
        return@withContext "❌ Connection Error: ${e.message}"
    }
}
