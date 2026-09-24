package com.hanbit.hakdang

import android.app.WallpaperManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.Shader
import android.graphics.Typeface
import android.os.Build
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.util.DisplayMetrics
import android.view.WindowManager
import kotlin.math.max
import kotlin.math.min

/**
 * Draws the word of the day onto a lock-screen wallpaper. Works on every
 * Android version and brand, unlike lock-screen widgets.
 */
object LockWallpaper {

    fun apply(ctx: Context, w: Word): Boolean = try {
        val (sw, sh) = screenSize(ctx)
        WallpaperManager.getInstance(ctx).setBitmap(render(w, sw, sh), null, true, WallpaperManager.FLAG_LOCK)
        true
    } catch (e: Exception) {
        false
    }

    private fun screenSize(ctx: Context): Pair<Int, Int> {
        val wm = ctx.getSystemService(WindowManager::class.java)
        val (a, b) = if (Build.VERSION.SDK_INT >= 30) {
            wm.maximumWindowMetrics.bounds.let { it.width() to it.height() }
        } else {
            val m = DisplayMetrics()
            @Suppress("DEPRECATION") wm.defaultDisplay.getRealMetrics(m)
            m.widthPixels to m.heightPixels
        }
        return min(a, b) to max(a, b)   // always portrait
    }

    fun render(w: Word, width: Int, height: Int): Bitmap {
        val bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        val W = width.toFloat()
        val H = height.toFloat()

        // Background: night indigo with a celadon glow
        c.drawRect(0f, 0f, W, H, Paint().apply {
            shader = LinearGradient(0f, 0f, 0f, H, 0xFF22384A.toInt(), 0xFF121820.toInt(), Shader.TileMode.CLAMP)
        })
        c.drawRect(0f, 0f, W, H, Paint().apply {
            shader = RadialGradient(W * 0.3f, H * 0.18f, W * 0.9f, 0x664F8572, 0x00000000, Shader.TileMode.CLAMP)
        })

        val cx = W / 2f
        var y = H * 0.44f   // below the lock-screen clock

        // Each hanja in its own practice-notebook square
        val chars = w.hanja.toList()
        if (chars.isNotEmpty()) {
            val box = min(W * 0.24f, (W * 0.84f) / chars.size)
            val left = cx - box * chars.size / 2f
            val frame = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = box * 0.02f; color = 0xCCE3A7A0.toInt() }
            val guide = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                style = Paint.Style.STROKE; strokeWidth = box * 0.008f; color = 0x88E3A7A0.toInt()
                pathEffect = DashPathEffect(floatArrayOf(box * 0.04f, box * 0.04f), 0f)
            }
            val hp = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = 0xFFF6F7F1.toInt(); textSize = box * 0.68f; textAlign = Paint.Align.CENTER
                typeface = Typeface.create(Typeface.SERIF, Typeface.NORMAL)
            }
            chars.forEachIndexed { i, ch ->
                val x0 = left + i * box
                c.drawRect(x0, y, x0 + box, y + box, frame)
                c.drawLine(x0 + box / 2, y, x0 + box / 2, y + box, guide)
                c.drawLine(x0, y + box / 2, x0 + box, y + box / 2, guide)
                val fm = hp.fontMetrics
                c.drawText(ch.toString(), x0 + box / 2, y + box / 2 - (fm.ascent + fm.descent) / 2, hp)
            }
            y += box + W * 0.1f
        }

        // Hangul word
        val ko = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = 0xFFFFFFFF.toInt(); textAlign = Paint.Align.CENTER; typeface = Typeface.DEFAULT_BOLD
            textSize = W * 0.13f
        }
        while (ko.measureText(w.ko) > W * 0.86f && ko.textSize > 20f) ko.textSize *= 0.9f
        c.drawText(w.ko, cx, y, ko)
        y += W * 0.075f

        // 훈음 line
        if (w.hunum.isNotBlank()) {
            val hp = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = 0xFFCFE3DA.toInt(); textAlign = Paint.Align.CENTER; textSize = W * 0.048f
            }
            while (hp.measureText(w.hunum) > W * 0.86f && hp.textSize > 14f) hp.textSize *= 0.92f
            c.drawText(w.hunum, cx, y, hp)
            y += W * 0.045f
        }

        // English meaning, wrapped
        val tp = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xFFB8C6D0.toInt(); textSize = W * 0.042f }
        val layout = StaticLayout.Builder.obtain(w.en, 0, w.en.length, tp, (W * 0.8f).toInt())
            .setAlignment(Layout.Alignment.ALIGN_CENTER).setMaxLines(3).build()
        c.save(); c.translate(W * 0.1f, y); layout.draw(c); c.restore()
        y += layout.height + W * 0.06f

        val tag = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = 0xFFE2B236.toInt(); textAlign = Paint.Align.CENTER; textSize = W * 0.032f
        }
        c.drawText(if (w.isNew) "오늘의 새 단어" else "오늘의 단어", cx, y, tag)
        return bmp
    }
}
