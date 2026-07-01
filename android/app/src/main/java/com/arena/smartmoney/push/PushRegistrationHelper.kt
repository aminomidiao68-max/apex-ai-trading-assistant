package com.arena.smartmoney.push

import android.os.Build
import com.arena.smartmoney.data.repository.TradingRepository
import com.arena.smartmoney.data.session.SessionManager
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object PushRegistrationHelper {
    fun registerCurrentDevice(sessionManager: SessionManager, repository: TradingRepository = TradingRepository()) {
        val authToken = sessionManager.getToken() ?: return
        runCatching {
            FirebaseMessaging.getInstance().token.addOnSuccessListener { fcmToken ->
                CoroutineScope(Dispatchers.IO).launch {
                    runCatching {
                        repository.registerDeviceToken(
                            authorization = "Bearer $authToken",
                            token = fcmToken,
                            deviceName = "Android ${Build.MODEL}"
                        )
                    }
                }
            }
        }
    }
}
