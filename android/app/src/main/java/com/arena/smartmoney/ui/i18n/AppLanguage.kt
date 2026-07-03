package com.arena.smartmoney.ui.i18n

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.arena.smartmoney.data.preferences.AppPreferencesManager

object AppLanguageState {
    var current by mutableStateOf("fa")
}

@Composable
fun rememberTranslator(): (String, String) -> String {
    val context = LocalContext.current
    remember { AppPreferencesManager(context) }
    val currentLanguage = AppLanguageState.current
    return remember(currentLanguage) {
        { en: String, fa: String -> if (currentLanguage == "fa") fa else en }
    }
}
