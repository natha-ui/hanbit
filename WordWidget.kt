package com.hanbit.hakdang

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.text.style.RelativeSizeSpan
import android.util.SizeF
import android.widget.RemoteViews

/**
 * Word-of-the-day widget. It picks a layout for the space it actually has,
 * and the text shrinks to fit, so nothing is cut off on small or narrow screens
 * (Fold cover screen, 2x1 slots) and it fills big ones.
 */
open class WordWidget : AppWidgetProvider() {

    protected open val cover = false

    override fun onUpdate(ctx: Context, mgr: AppWidgetManager, ids: IntArray) {
        val w = WordRepository(ctx).wordOfDay()
        ids.forEach { mgr.updateAppWidget(it, build(ctx, w, mgr.getAppWidgetOptions(it), cover)) }
    }

    override fun onAppWidgetOptionsChanged(ctx: Context, mgr: AppWidgetManager, id: Int, opts: Bundle) {
        mgr.updateAppWidget(id, build(ctx, WordRepository(ctx).wordOfDay(), opts, cover))
    }

    companion object {
        private fun title(w: Word): CharSequence {
            val sb = SpannableStringBuilder(w.ko)
            if (w.hanja.isNotEmpty()) {
                val start = sb.length + 1
                sb.append(" ").append(w.hanja)
                sb.setSpan(RelativeSizeSpan(0.72f), start, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                sb.setSpan(ForegroundColorSpan(0xFFCFE3DA.toInt()), start, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            return sb
        }

        private fun fill(ctx: Context, layout: Int, w: Word): RemoteViews {
            val v = RemoteViews(ctx.packageName, layout)
            val tag = if (w.isNew) "오늘의 새 단어" else "오늘의 단어"
            v.setTextViewText(R.id.w_main, title(w))
            when (layout) {
                R.layout.widget_medium ->
                    v.setTextViewText(R.id.w_sub, listOf(w.hunum, w.en).filter { it.isNotBlank() }.joinToString("  ·  "))
                R.layout.widget_large, R.layout.widget_cover -> {
                    v.setTextViewText(R.id.w_tag, tag)
                    v.setTextViewText(R.id.w_hunum, w.hunum)
                    v.setTextViewText(R.id.w_en, w.en)
                }
            }
            val open = PendingIntent.getActivity(
                ctx, 0, Intent(ctx, MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
            )
            v.setOnClickPendingIntent(R.id.w_root, open)
            return v
        }

        fun build(ctx: Context, w: Word, opts: Bundle?, cover: Boolean): RemoteViews {
            if (cover) return fill(ctx, R.layout.widget_cover, w)
            if (Build.VERSION.SDK_INT >= 31) {
                // The launcher picks the biggest layout that fits the widget's current size
                return RemoteViews(
                    mapOf(
                        SizeF(40f, 40f) to fill(ctx, R.layout.widget_small, w),
                        SizeF(170f, 60f) to fill(ctx, R.layout.widget_medium, w),
                        SizeF(170f, 115f) to fill(ctx, R.layout.widget_large, w),
                    ),
                )
            }
            val wdp = opts?.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH, 250) ?: 250
            val hdp = opts?.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT, 110) ?: 110
            val layout = when {
                wdp < 170 -> R.layout.widget_small
                hdp < 115 -> R.layout.widget_medium
                else -> R.layout.widget_large
            }
            return fill(ctx, layout, w)
        }

        fun refreshAll(ctx: Context) {
            val mgr = AppWidgetManager.getInstance(ctx)
            val w by lazy { WordRepository(ctx).wordOfDay() }
            for ((cls, isCover) in listOf(WordWidget::class.java to false, CoverWordWidget::class.java to true)) {
                mgr.getAppWidgetIds(ComponentName(ctx, cls)).forEach { id ->
                    mgr.updateAppWidget(id, build(ctx, w, mgr.getAppWidgetOptions(id), isCover))
                }
            }
        }
    }
}

/** Same word, laid out as one full page for the Galaxy Z Flip cover screen. */
class CoverWordWidget : WordWidget() {
    override val cover = true
}
