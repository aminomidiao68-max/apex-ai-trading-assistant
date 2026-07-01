package com.arena.smartmoney.push

import com.arena.smartmoney.data.session.SessionManager
import com.arena.smartmoney.util.NotificationHelper
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class ApexFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        PushRegistrationHelper.registerCurrentDevice(SessionManager(applicationContext))
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val title = message.notification?.title ?: message.data["title"] ?: "APEX AI"
        val body = message.notification?.body ?: message.data["body"] ?: "New trading notification"
        NotificationHelper.showSignalNotification(
            context = applicationContext,
            title = title,
            body = body,
            id = (System.currentTimeMillis() % Int.MAX_VALUE).toInt()
        )
    }
}
