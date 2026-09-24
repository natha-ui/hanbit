package com.hanbit.hakdang

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

/** Home-screen and lock-screen widget showing the word of the day. */
class WordWidget : AppWidgetProvider() {

    override fun onUpdate(ctx: Context, mgr: AppWidgetManager, ids: IntArray) {
        val w = WordRepository(ctx).wordOfDay()
        ids.forEach { mgr.updateAppWidget(it, views(ctx, w)) }
    }

    companion object {
        private fun views(ctx: Context, w: Word): RemoteViews {
            val v = RemoteViews(ctx.packageName, R.layout.widget_word)
            v.setTextViewText(R.id.w_tag, if (w.isNew) "오늘의 새 단어 · new today" else "오늘의 단어 · review")
            v.setTextViewText(R.id.w_ko, w.ko)
            v.setTextViewText(R.id.w_hanja, w.hanja)
            v.setTextViewText(R.id.w_hunum, w.hunum)
            v.setTextViewText(R.id.w_en, w.en)
            val open = PendingIntent.getActivity(
                ctx, 0, Intent(ctx, MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
            )
            v.setOnClickPendingIntent(R.id.w_root, open)
            return v
        }

        fun refreshAll(ctx: Context) {
            val mgr = AppWidgetManager.getInstance(ctx)
            val ids = mgr.getAppWidgetIds(ComponentName(ctx, WordWidget::class.java))
            if (ids.isEmpty()) return
            val w = WordRepository(ctx).wordOfDay()
            ids.forEach { mgr.updateAppWidget(it, views(ctx, w)) }
        }
    }
}
