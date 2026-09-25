# 한빛 학당

Korean taught the way Korean children learn it: Hangul first, then hanja by 훈음
(meaning + sound), then words built from those characters, grammar, graded stories
and tests. New words and stories arrive every day from trending topics, and the word
of the day appears on your lock screen, on Android or iPhone.

## What's here

- `web/`: the course. It is the iPhone app, and the Android app now loads it too.
- `android/`: the Android app. It adds speech, widgets (including the Galaxy Z Flip cover screen) and the lock-screen wallpaper.
- `iphone/Hanbit.js`: the iPhone lock-screen widget, run by the free Scriptable app.
- `pipeline/`: each day's trending words and stories, written to `data/words.json`.
- `.github/workflows/`: the daily update, website publishing and the APK builder.

## Do I need to reinstall when something changes?

| What changed | iPhone | Android |
|---|---|---|
| Daily words and stories | Automatic | Automatic |
| Course content: words, stories, tests, grammar, layout (anything in `web/`) | Automatic | Automatic, once your site address is set in the app |
| Widgets, wallpaper, speech (anything in `android/`) | n/a | New APK, installed over the old one. Progress is kept. |

Changes reach your phone the next time you open the app while online.

**One-time step for this update on Android:** earlier APKs were each signed with a
throwaway key, so Android won't let this one install over them.
1. In the old app, open 설정 › Back up your progress › **Copy backup**, and paste it into a note.
2. Uninstall the old app, then install the new APK.
3. Restore the backup in 설정.

All APKs from now on share the key in `android/keystore/`, so updates install over the
top and keep your progress. (Anyone with this repo could sign an APK as "your" app.
That only matters if you install APKs from other people, and you won't.)

## 1. Shared setup (once)

1. Create a **public** GitHub repository called `hanbit` and upload the *contents* of this folder.
   Make sure the hidden `.github` folder is included.
2. Go to Settings › Pages › Source and choose **GitHub Actions**.
3. Optional, under Settings › Secrets and variables › Actions:
   - `KRDICT_KEY`: a free key from https://krdict.korean.go.kr/openApi/openApiInfo. It adds learner
     levels (초급/중급/고급), which is how daily words get harder as you progress.
   - `ANTHROPIC_API_KEY`: a key from https://console.anthropic.com. Each day it writes two
     original stories from the day's words: an easy one and a harder one, with English and test
     questions. It costs a few cents a day. Without it, the daily story is the opening of a trending
     topic's Korean Wikipedia article (no translation; test questions are fill-in-the-blank).
4. Go to Actions › **Daily words** › Run workflow. Your site is then live at
   `https://YOUR-NAME.github.io/hanbit/` and updates every morning.

## 2. iPhone

**App:** open your site in Safari, then tap Share › **Add to Home Screen**. Always open it from that icon.
If audio is silent, go to Settings › Accessibility › Spoken Content › Voices › Korean and download a voice.

**Lock-screen word:**
1. Install **Scriptable**. Tap **+** and paste in `iphone/Hanbit.js`.
2. Set the `SITE` line to your address and name the script **Hanbit**.
3. Add a Scriptable widget to the lock screen (rectangular size) and choose **Hanbit** as its Script.
4. Every few days, tap **Update my iPhone widget** on the app's Today screen, so the widget knows your level.

## 3. Android (including Galaxy Z Flip and Fold)

1. Go to Actions › **Build APK** › Run workflow. Download `hanbit-apk`, unzip it, and install the APK
   (allow "install unknown apps").
2. In the app, open 설정 and enter your site address: `https://YOUR-NAME.github.io/hanbit/`.
   The app reloads from your site; from then on, course updates arrive by themselves.
3. Tick **Put the word of the day on my lock-screen wallpaper** (works on every phone).
4. Widgets:
   - **Home screen, any phone:** add **오늘의 단어**. Resize it freely; below about 170 × 60 dp
     it shows just the word, and bigger sizes add the 훈음 and meaning. Text shrinks to fit rather than
     being cut off.
   - **Galaxy Z Flip cover screen:** Settings › Cover screen › Widgets, then turn on
     **오늘의 단어 (cover screen)**. It fills the whole cover screen. If it isn't listed (Samsung
     changes this between One UI versions), install Good Lock › MultiStar › "I ♡ Galaxy Foldable".
   - **Galaxy Z Fold cover screen:** it is a normal home screen, so add the regular widget there.
     It adapts to the narrower width.
   - **Pixel / stock Android 16 QPR2+ lock screen:** Settings › Display › Lock screen ›
     Widgets on lock screen.

## Subjects

The 주제 (Subjects) tab has vocabulary for eight subjects: maths, science, engineering, business &
economics, culture & arts, philosophy, history, and medicine & health. There are about 40 core words
each, and every day's update adds up to 3 more per subject.

- **Where the daily words come from:** each subject reads one Korean Wikipedia article a day. It starts
  from a list of topic articles and then follows links from the ones it has read. It keeps the
  Sino-Korean terms that appear more than once, with their hanja, 훈음, English and the sentence they appeared in.
- **Studying:** tap **Add to my daily study** on any subject and its words join your sessions (about one
  new card in four, rotating across the subjects you've switched on, alternating core and newly added words).
- **Tests:** each subject has its own test.
- **Changing the subjects:** edit `SUBJECT_SEEDS` in `pipeline/daily_words.py` to change the starting articles,
  or `--per-subject` in `.github/workflows/daily-words.yml` to change how many words each subject gets a day.

## How it gets harder

- There are about 1,000 built-in words: roughly 700 across the three levels plus about 320 subject words.
  - **Level 1:** the 50 characters of the 8급 exam, plus everyday native words (numbers, body, nature, basic verbs).
  - **Level 2:** 7급 characters (seasons, nature, family, time) and more native words.
  - **Level 3:** 6급 characters and everyday words for school, shops, travel and polite phrases (감사, 미안, 안녕).
- Native words are spread between the characters instead of arriving in one block.
- About one in four new cards comes from the news, matched to your level: 초급, then 중급 after
  300 items learned, then 고급 after 900.
- Tests:
  - **Words tab:** "시험 보기" gives 10 questions (meaning, word, hanja, 훈음) for the level you choose.
    Missed words go straight back into today's review.
  - **Stories:** every story ends with a test (comprehension questions plus fill-in-the-blank).
