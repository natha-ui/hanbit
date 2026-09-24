# 한빛 학당

Korean taught the way Korean children learn it: Hangul first, then hanja by 훈음
(meaning + sound), then words built from those characters, grammar and graded stories.
New words arrive every day from trending topics, and the word of the day appears on
your lock screen, on Android or iPhone.

## What's here

- `web/`: the course, which is the iPhone app (served free by GitHub Pages).
- `android/`: the Android app. It wraps the same course and adds speech, a widget and a lock-screen wallpaper.
- `iphone/Hanbit.js`: the iPhone lock-screen widget script, for the free Scriptable app.
- `pipeline/`: collects today's trending words into `data/words.json`.
- `.github/workflows/`: daily words and website publishing, plus an APK builder.

## 1. Shared setup (once, about 10 minutes)

1. Create a **public** GitHub repository called `hanbit` and upload this folder.
   It only holds the course and vocabulary. Your progress stays on your phone.
2. In the repo, go to Settings › Pages › Build and deployment › Source, and choose **GitHub Actions**.
3. (Recommended) Get a free dictionary key at https://krdict.korean.go.kr/openApi/openApiInfo.
   Add it under Settings › Secrets and variables › Actions as `KRDICT_KEY`.
   It adds learner levels (초급/중급/고급), which is how new words get harder as you progress.
4. Go to Actions › **Daily words** › Run workflow. When it finishes, your app is live at
   `https://YOUR-NAME.github.io/hanbit/`, and it updates itself every morning.

## 2. iPhone

### The app
1. Open `https://YOUR-NAME.github.io/hanbit/` in **Safari**.
2. Tap Share › **Add to Home Screen**.
3. Always open it from the home-screen icon. It runs full-screen, works offline, and keeps
   your progress separate from Safari. Now and then, copy a backup from 설정 (Settings) › Back up your progress.
4. If audio is silent or robotic, go to iPhone Settings › Accessibility › Spoken Content ›
   Voices › Korean, and download a voice (e.g. Yuna, the Enhanced version).

### The lock-screen word
1. Install **Scriptable** (free) from the App Store.
2. In Scriptable, tap **+**, paste in the contents of `iphone/Hanbit.js`, and change the
   `SITE` line to your address. Rename the script (tap its title) to exactly **Hanbit**.
3. Tap ▶ once to check it shows a word.
4. Long-press the lock screen › Customize › Lock Screen › tap the widget area › add
   **Scriptable**. Choose the rectangular size (it shows word, hanja, 훈음 and meaning),
   then tap it and pick **Hanbit** as the Script.
5. After a study session every few days, open 한빛 학당 and tap **Update my iPhone widget**
   (on the Today screen). This sends your level to the widget, so it picks words that
   are right for you and reviews words you already know.

## 3. Android

1. Go to Actions › **Build APK** › Run workflow. Download `hanbit-apk` from the finished run
   and unzip it. You can also open the `android` folder in Android Studio and press Run.
2. Copy the APK to your phone and open it. Allow "install unknown apps" when asked.
3. In the app, open 설정 and paste the daily-words address:
   `https://YOUR-NAME.github.io/hanbit/data/words.json`
   Then tick **Put the word of the day on my lock-screen wallpaper**.
4. Optional lock-screen widget:
   - Pixel and other stock-Android phones on Android 16 QPR2 or later: Settings › Display ›
     Lock screen › Widgets on lock screen, then add **오늘의 단어**.
   - Samsung decides which widgets its lock screen allows. If it isn't offered, the wallpaper option covers it.

## How it gets harder
- The course order is Hangul, then the 50 characters of the 8급 exam, the words they unlock, 7급 characters, grammar, and stories.
- Words from the news are mixed into each session, about one in four new cards.
- Only words at your level are chosen: 초급 until 300 items are learned, then 중급, then 고급 after 900.
- The lock screen (on both phones) shows a new trending word most days, and a word you already know about one day in three.
