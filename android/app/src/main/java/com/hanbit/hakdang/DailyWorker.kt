package com.hanbit.hakdang

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.Duration
import java.time.LocalDateTime
import java.util.concurrent.TimeUnit

/** Every morning: fetch new words, pick the word of the day, update widget and lock screen. */
class DailyWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val repo = WordRepository(applicationContext)
        repo.download()                     // fine if offline: yesterday's words are kept
        val word = repo.wordOfDay()
        WordWidget.refreshAll(applicationContext)
        if (repo.wallpaper) LockWallpaper.apply(applicationContext, word)
        Result.success()
    }

    companion object {
        fun schedule(ctx: Context) {
            val now = LocalDateTime.now()
            var next = now.withHour(5).withMinute(30).withSecond(0)
            if (!next.isAfter(now)) next = next.plusDays(1)
            val req = PeriodicWorkRequestBuilder<DailyWorker>(24, TimeUnit.HOURS)
                .setInitialDelay(Duration.between(now, next).toMinutes(), TimeUnit.MINUTES)
                .build()
            WorkManager.getInstance(ctx)
                .enqueueUniquePeriodicWork("daily-words", ExistingPeriodicWorkPolicy.KEEP, req)
        }

        fun runNow(ctx: Context) {
            WorkManager.getInstance(ctx).enqueueUniqueWork(
                "daily-now", ExistingWorkPolicy.REPLACE, OneTimeWorkRequestBuilder<DailyWorker>().build(),
            )
        }
    }
}
