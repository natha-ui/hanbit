package com.hanbit.hakdang

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class Word(
    val ko: String,
    val hanja: String,
    val en: String,
    val hunum: String,
    val grade: String = "",
    val isNew: Boolean = false,
) {
    fun toJson(): String = JSONObject()
        .put("ko", ko).put("hanja", hanja).put("en", en)
        .put("hunum", hunum).put("grade", grade).put("isNew", isNew)
        .toString()

    companion object {
        fun from(o: JSONObject) = Word(
            o.optString("ko"), o.optString("hanja"), o.optString("en"),
            o.optString("hunum"), o.optString("grade"), o.optBoolean("isNew"),
        )
    }
}

/** Stores the downloaded daily words, the learner's level, and picks the lock-screen word. */
class WordRepository(private val ctx: Context) {

    private val prefs = ctx.getSharedPreferences("hanbit", Context.MODE_PRIVATE)
    private val dailyFile get() = File(ctx.filesDir, "words.json")

    /** GitHub Pages address, e.g. https://you.github.io/hanbit/ — the course and words load from here. */
    var site: String
        get() = prefs.getString("site", "") ?: ""
        set(v) {
            var s = v.trim()
            if (s.isNotEmpty() && !s.endsWith("/")) s += "/"
            prefs.edit().putString("site", if (s.startsWith("https://")) s else "").apply()
        }

    /** Where daily words come from: the site, or an older raw-GitHub address if one was saved. */
    var url: String
        get() = site.takeIf { it.isNotEmpty() }?.let { it + "data/words.json" } ?: (prefs.getString("url", "") ?: "")
        set(v) = prefs.edit().putString("url", v.trim()).apply()

    var wallpaper: Boolean
        get() = prefs.getBoolean("wallpaper", false)
        set(v) = prefs.edit().putBoolean("wallpaper", v).apply()

    private val lastUpdate: String get() = prefs.getString("lastUpdate", "") ?: ""

    fun settingsJson(): String = JSONObject()
        .put("site", site).put("url", url).put("wallpaper", wallpaper).put("lastUpdate", lastUpdate).toString()

    fun dailyJson(): String = if (dailyFile.exists()) dailyFile.readText() else "{}"

    fun saveState(json: String) = prefs.edit().putString("state", json).apply()

    /** Full copy of learning progress, so it survives switching between the built-in and online course. */
    private val progressFile get() = File(ctx.filesDir, "progress.json")
    fun saveProgress(json: String) {
        if (json.length > 2 && json.length < 20_000_000) progressFile.writeText(json)
    }
    fun loadProgress(): String = if (progressFile.exists()) progressFile.readText() else ""

    /** Downloads words.json from the configured address. Returns true if it changed. */
    fun download(): Boolean {
        val u = url
        if (u.isBlank()) return false
        return try {
            val c = URL(u).openConnection() as HttpURLConnection
            c.connectTimeout = 15_000
            c.readTimeout = 20_000
            c.setRequestProperty("Cache-Control", "no-cache")
            val body = c.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            c.disconnect()
            JSONObject(body).getJSONArray("days")          // reject anything that isn't our format
            dailyFile.writeText(body)
            prefs.edit()
                .putString("lastUpdate", SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.UK).format(Date()))
                .putString("lockDate", "")                    // re-pick with the fresh words
                .apply()
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun today() = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date())

    fun hasPickedToday() = prefs.getString("lockDate", "") == today()

    fun wordOfDay(): Word {
        val t = today()
        if (prefs.getString("lockDate", "") == t) {
            prefs.getString("lockWord", null)?.let { s ->
                runCatching { return Word.from(JSONObject(s)) }
            }
        }
        val w = pick(t)
        prefs.edit().putString("lockDate", t).putString("lockWord", w.toJson()).apply()
        return w
    }

    /**
     * Most days: a new word from today's trending topics, at a difficulty that
     * matches how much has been learned. About one day in three once 20+ words
     * are known: a review of a word already learned.
     */
    private fun pick(day: String): Word {
        val state = prefs.getString("state", null)?.let { runCatching { JSONObject(it) }.getOrNull() }
        val learned = state?.optInt("learned", 0) ?: 0
        val known = mutableListOf<Word>()
        state?.optJSONArray("known")?.let { a -> for (i in 0 until a.length()) known += Word.from(a.getJSONObject(i)) }
        val knownKo = known.map { it.ko }.toSet()

        val prefer = when {
            learned < 300 -> listOf("초급", "")
            learned < 900 -> listOf("중급", "초급", "")
            else -> listOf("고급", "중급", "초급", "")
        }
        val hash = day.hashCode() and 0x7fffffff
        val reviewDay = known.size >= 20 && hash % 3 == 0

        if (!reviewDay) {
            val fresh = latestDaily().filter { it.ko !in knownKo && it.hanja.isNotEmpty() }
            for (g in prefer) fresh.firstOrNull { it.grade == g }?.let { return it.copy(isNew = true) }
        }
        if (known.isNotEmpty()) return known[hash % known.size]
        val base = baseWords()
        return if (base.isNotEmpty()) base[hash % base.size] else Word("학교", "學校", "school", "배울 학 · 학교 교")
    }

    private fun latestDaily(): List<Word> = runCatching {
        val days = JSONObject(dailyJson()).getJSONArray("days")
        if (days.length() == 0) return emptyList()
        val words = days.getJSONObject(days.length() - 1).getJSONArray("words")
        (0 until words.length()).map { i ->
            val o = words.getJSONObject(i)
            val chars = o.optJSONArray("chars") ?: JSONArray()
            val hunum = (0 until chars.length()).joinToString(" · ") { j ->
                val c = chars.getJSONObject(j)
                "${c.optString("hun")} ${c.optString("eum")}".trim()
            }
            Word(o.optString("ko"), o.optString("hanja"), o.optString("en"), hunum, o.optString("grade"))
        }
    }.getOrDefault(emptyList())

    private fun baseWords(): List<Word> = runCatching {
        val a = JSONArray(ctx.assets.open("base_words.json").bufferedReader().use { it.readText() })
        (0 until a.length()).map { Word.from(a.getJSONObject(it)) }
    }.getOrDefault(emptyList())
}
