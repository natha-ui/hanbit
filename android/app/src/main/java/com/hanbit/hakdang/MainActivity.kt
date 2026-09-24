package com.hanbit.hakdang

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.res.Configuration
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import org.json.JSONObject
import java.util.Locale
import java.util.UUID

/**
 * Hosts the course in a WebView. When a site address is set, the course loads
 * from GitHub Pages (so content updates need no reinstall); otherwise, or when
 * offline on first run, it uses the copy built into the app.
 */
class MainActivity : Activity(), TextToSpeech.OnInitListener {

    private lateinit var web: WebView
    private lateinit var repo: WordRepository
    private var tts: TextToSpeech? = null
    @Volatile private var ttsReady = false
    private var fellBack = false

    private val bundled = "file:///android_asset/index.html"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repo = WordRepository(this)

        val dark = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        val paper = if (dark) 0xFF121720.toInt() else 0xFFE9ECE3.toInt()

        // Draw behind the system bars ourselves, then pad the content clear of them.
        // (Padding a WebView directly doesn't work, so it sits inside a frame.)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        @Suppress("DEPRECATION")
        run { window.statusBarColor = Color.TRANSPARENT; window.navigationBarColor = Color.TRANSPARENT }

        val frame = FrameLayout(this)
        frame.setBackgroundColor(paper)
        web = WebView(this)
        web.setBackgroundColor(paper)
        frame.addView(web, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        setContentView(frame)

        ViewCompat.setOnApplyWindowInsetsListener(frame) { v, insets ->
            val b = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout() or WindowInsetsCompat.Type.ime(),
            )
            v.setPadding(b.left, b.top, b.right, b.bottom)
            WindowInsetsCompat.CONSUMED
        }
        WindowInsetsControllerCompat(window, frame).apply {
            isAppearanceLightStatusBars = !dark
            isAppearanceLightNavigationBars = !dark
        }

        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.mediaPlaybackRequiresUserGesture = false
        web.webViewClient = Client()
        web.addJavascriptInterface(Bridge(), "Hanbit")

        if (savedInstanceState == null) web.loadUrl(startUrl()) else web.restoreState(savedInstanceState)

        tts = TextToSpeech(this, this)
        DailyWorker.schedule(this)
        if (!repo.hasPickedToday()) DailyWorker.runNow(this)
    }

    private fun startUrl() = repo.site.ifEmpty { bundled }

    /** Only our own pages run inside the app; any other link opens in the browser. */
    private inner class Client : WebViewClient() {
        private fun ours(u: Uri): Boolean {
            if (u.scheme == "file") return true
            val site = repo.site
            return site.isNotEmpty() && u.toString().startsWith(site)
        }

        override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest): Boolean {
            if (ours(req.url)) return false
            runCatching { startActivity(Intent(Intent.ACTION_VIEW, req.url)) }
            return true
        }

        override fun onReceivedError(view: WebView, req: WebResourceRequest, err: WebResourceError) {
            // Offline before the site was ever cached: use the built-in course
            if (req.isForMainFrame && !fellBack && req.url.scheme != "file") {
                fellBack = true
                view.loadUrl(bundled)
            }
        }
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
        @JavascriptInterface fun syncState(json: String) = repo.saveState(json)
        @JavascriptInterface fun saveProgress(json: String) = repo.saveProgress(json)
        @JavascriptInterface fun loadProgress(): String = repo.loadProgress()

        @JavascriptInterface
        fun setSettings(json: String) {
            val o = runCatching { JSONObject(json) }.getOrNull() ?: return
            val turnedOn = o.optBoolean("wallpaper") && !repo.wallpaper
            val oldSite = repo.site
            if (o.has("site")) repo.site = o.optString("site")
            if (o.has("url")) repo.url = o.optString("url")
            repo.wallpaper = o.optBoolean("wallpaper", repo.wallpaper)
            val siteChanged = repo.site != oldSite
            if (turnedOn || siteChanged) DailyWorker.runNow(this@MainActivity)
            if (siteChanged) runOnUiThread { fellBack = false; web.loadUrl(startUrl()) }
        }

        @JavascriptInterface
        fun refreshNow() {
            DailyWorker.runNow(this@MainActivity)
        }

        @JavascriptInterface
        fun openTtsSettings() {
            runOnUiThread { runCatching { startActivity(Intent("com.android.settings.TTS_SETTINGS")) } }
        }
    }
}
