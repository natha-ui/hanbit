package com.hanbit.hakdang

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import android.view.WindowInsets
import org.json.JSONObject
import java.util.Locale
import java.util.UUID

/**
 * Hosts the learning app (assets/index.html) in a WebView and gives it
 * what a web page can't do alone: Korean speech, daily words and the lock screen.
 */
class MainActivity : Activity(), TextToSpeech.OnInitListener {

    private lateinit var web: WebView
    private lateinit var repo: WordRepository
    private var tts: TextToSpeech? = null
    @Volatile private var ttsReady = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repo = WordRepository(this)

        web = WebView(this)
        val dark = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        web.setBackgroundColor(if (dark) 0xFF121720.toInt() else 0xFFE9ECE3.toInt())
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true            // keeps progress (localStorage)
        web.settings.mediaPlaybackRequiresUserGesture = false
        web.webViewClient = WebViewClient()
        web.addJavascriptInterface(Bridge(), "Hanbit")
        setContentView(web)

        // Android 15+ draws apps edge to edge: keep the page clear of the system bars
        if (Build.VERSION.SDK_INT >= 35) {
            web.setOnApplyWindowInsetsListener { v, insets ->
                val b = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())
                v.setPadding(b.left, b.top, b.right, b.bottom)
                insets
            }
        }

        if (savedInstanceState == null) web.loadUrl("file:///android_asset/index.html")
        else web.restoreState(savedInstanceState)

        tts = TextToSpeech(this, this)
        DailyWorker.schedule(this)
        if (!repo.hasPickedToday()) DailyWorker.runNow(this)
    }

    override fun onInit(status: Int) {
        val engine = tts ?: return
        if (status != TextToSpeech.SUCCESS) return
        val r = engine.setLanguage(Locale.KOREAN)
        ttsReady = r != TextToSpeech.LANG_MISSING_DATA && r != TextToSpeech.LANG_NOT_SUPPORTED
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(id: String?) {}
            override fun onDone(id: String?) = finished(id)
            @Deprecated("Deprecated in Java")
            override fun onError(id: String?) = finished(id)
        })
    }

    private fun finished(id: String?) {
        if (id == null) return
        runOnUiThread { web.evaluateJavascript("window.__ttsDone&&window.__ttsDone('$id')", null) }
    }

    override fun onResume() {
        super.onResume()
        WordWidget.refreshAll(this)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    override fun onDestroy() {
        tts?.shutdown()
        web.destroy()
        super.onDestroy()
    }

    /** Methods the page can call as window.Hanbit.xxx() */
    inner class Bridge {
        @JavascriptInterface
        fun speak(text: String, rate: Float, flush: Boolean): String {
            val id = UUID.randomUUID().toString()
            tts?.setSpeechRate(rate)
            tts?.speak(text, if (flush) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD, null, id)
            return id
        }

        @JavascriptInterface fun ttsOk(): Boolean = ttsReady
        @JavascriptInterface fun dailyWords(): String = repo.dailyJson()
        @JavascriptInterface fun lockWord(): String = repo.wordOfDay().toJson()
        @JavascriptInterface fun getSettings(): String = repo.settingsJson()

        @JavascriptInterface
        fun syncState(json: String) {
            repo.saveState(json)
        }

        @JavascriptInterface
        fun setSettings(json: String) {
            val o = runCatching { JSONObject(json) }.getOrNull() ?: return
            val turnedOn = o.optBoolean("wallpaper") && !repo.wallpaper
            repo.url = o.optString("url", repo.url)
            repo.wallpaper = o.optBoolean("wallpaper", repo.wallpaper)
            if (turnedOn) DailyWorker.runNow(this@MainActivity)
        }

        @JavascriptInterface
        fun refreshNow() {
            DailyWorker.runNow(this@MainActivity)
        }

        @JavascriptInterface
        fun openTtsSettings() {
            runOnUiThread {
                runCatching { startActivity(Intent("com.android.settings.TTS_SETTINGS")) }
            }
        }
    }
}
