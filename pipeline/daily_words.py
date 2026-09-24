#!/usr/bin/env python3
"""
한빛 학당 — daily words pipeline.

Collects what Korea is talking about today (Google Trends, news RSS, most-read
Korean Wikipedia pages), finds the words that keep coming up, looks up their
hanja and English, and adds the 훈음 (meaning + sound) of every character.
Writes data/words.json, which the phone app downloads each morning.

Stories: with ANTHROPIC_API_KEY set, two original graded stories (easy and
harder) are written from the day's words, with translations and test questions.
Without it, the lead of a trending topic's Korean Wikipedia article is used.

Dictionary: set KRDICT_KEY (free key from krdict.korean.go.kr/openApi) for
learner-graded words (초급/중급/고급). Without it, English Wiktionary is used.

    python pipeline/daily_words.py --out data
"""
import argparse, collections, datetime as dt, html, json, os, re, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import requests

HERE = Path(__file__).parent
UA = {"User-Agent": "HanbitHakdang/0.2 (personal Korean study project)"}
KRDICT_KEY = os.environ.get("KRDICT_KEY", "").strip()
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "").strip() or "claude-sonnet-5"

TREND_FEEDS = ["https://trends.google.com/trending/rss?geo=KR"]
NEWS_FEEDS = [
    "https://www.yna.co.kr/rss/news.xml",
    "https://www.hani.co.kr/rss/",
    "https://rss.donga.com/total.xml",
]
# Words too generic (or too newsroom-specific) to be worth a card
STOP = set("""것 수 등 때 중 곳 점 뒤 앞 번 개 명 년 월 일 시 분 이번 오늘 어제 내일 지난 올해 최근 관련 기자 사진 뉴스
연합뉴스 속보 종합 단독 영상 포토 기사 제공 오전 오후 이후 이전 가운데 대해 통해 위해 경우 정도 사람 이날 당시 현재
전날 다음 해당 발표 진행 예정 지역 전국 서울 한국 국내 정부 대통령 위원 의원 사진기자 특파원""".split())


def log(*a):
    print(*a, file=sys.stderr)


def get(url, **kw):
    kw.setdefault("timeout", 20)
    return requests.get(url, headers=UA, **kw)


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


# ---------- 1. what is Korea reading today ----------
def rss_texts(url, trend=False):
    out = []
    try:
        root = ET.fromstring(get(url).content)
        for it in root.iter("item"):
            out.append(clean(it.findtext("title")))
            if trend:  # Google Trends nests the related headlines
                out += [clean(e.text) for e in it.iter() if e.tag.endswith("news_item_title")]
            else:
                out.append(clean(it.findtext("description"))[:300])
    except Exception as e:
        log("  feed failed:", url, e)
    return [t for t in out if t]


def wiki_top(day):
    y = day - dt.timedelta(days=1)
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/ko.wikipedia/all-access/{y:%Y/%m/%d}"
    try:
        arts = get(url).json()["items"][0]["articles"]
        return [a["article"].replace("_", " ") for a in arts
                if ":" not in a["article"] and a["article"] not in ("대문", "위키백과")][:60]
    except Exception as e:
        log("  wikipedia failed:", e)
        return []


def collect(day):
    trends = [t for u in TREND_FEEDS for t in rss_texts(u, trend=True)]
    news = [t for u in NEWS_FEEDS for t in rss_texts(u)]
    wiki = wiki_top(day)
    log(f"  texts: {len(trends)} trend, {len(news)} news, {len(wiki)} wikipedia")
    topics = []
    for t in trends:  # the trend titles themselves, for display
        if t and t not in topics and len(t) <= 20:
            topics.append(t)
    return trends, news, wiki, topics[:10]


# ---------- 2. find the words that keep coming up ----------
HANGUL = re.compile(r"^[가-힣]+$")


def candidates(trends, news, wiki, skip):
    from kiwipiepy import Kiwi
    kiwi = Kiwi()
    score = collections.Counter()
    example = {}
    for weight, texts in ((3, trends), (1, news), (2, wiki)):
        for text in texts:
            seen = set()
            for tok in kiwi.tokenize(text):
                if tok.tag == "NNG":
                    w = tok.form
                elif tok.tag in ("VV", "VA"):
                    w = tok.form + "다"
                else:
                    continue
                if len(w) < 2 or not HANGUL.match(w) or w in STOP or w in skip or w in seen:
                    continue
                seen.add(w)
                score[w] += weight
                if tok.tag == "NNG" and w not in example and 8 <= len(text) <= 80 and w in text:
                    example[w] = text
    return [w for w, s in score.most_common() if s >= 2], example


# ---------- 3. dictionary: hanja, English, learner grade ----------
def is_cjk(ch):
    o = ord(ch)
    return 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF


def only_hanja(origin, word):
    h = "".join(ch for ch in (origin or "") if is_cjk(ch))
    return h if len(h) == len(word) else ""  # must line up syllable-for-character


def krdict(word):
    r = requests.get("https://krdict.korean.go.kr/api/search", timeout=20, params={
        "key": KRDICT_KEY, "q": word, "part": "word", "translated": "y", "trans_lang": "1"})
    root = ET.fromstring(r.content)
    for item in root.iter("item"):
        if (item.findtext("word") or "").strip() != word:
            continue
        en = [t.strip() for t in (s.findtext("translation/trans_word") for s in item.iter("sense")) if t and t.strip()]
        if not en:
            continue
        return {"hanja": only_hanja(item.findtext("origin"), word),
                "en": "; ".join(dict.fromkeys(en))[:120],
                "grade": (item.findtext("word_grade") or "").strip(),
                "pos": (item.findtext("pos") or "").strip()}
    return None


LINK = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")


def strip_wiki(s):
    s = LINK.sub(r"\1", s)
    for _ in range(3):
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    return re.sub(r"'{2,}", "", s).strip(" ;,.")


def wikt_korean(page):
    r = get("https://en.wiktionary.org/w/api.php", params={
        "action": "parse", "page": page, "prop": "wikitext", "format": "json",
        "formatversion": "2", "redirects": "1"})
    j = r.json()
    if "error" in j:
        return ""
    txt = j["parse"]["wikitext"]
    m = re.search(r"^==\s*Korean\s*==\s*$", txt, re.M)
    if not m:
        return ""
    rest = txt[m.end():]
    n = re.search(r"^==[^=].*==\s*$", rest, re.M)
    return rest[: n.start()] if n else rest


def wiktionary(word):
    sec = wikt_korean(word)
    if not sec:
        return None
    m = re.search(r"\|\s*hanja\s*=\s*([^|}\n]+)", sec)
    gl = [strip_wiki(l[2:]) for l in sec.splitlines() if l.startswith("# ")]
    gl = [g for g in gl if g]
    if not gl:
        return None
    return {"hanja": only_hanja(m.group(1) if m else "", word),
            "en": "; ".join(gl[:2])[:120], "grade": "", "pos": ""}


# 훈음 for single characters: seed list first, then Wiktionary, cached
PARAM = r"((?:\[\[[^\]]*\]\]|[^|}\n])+)"


EUMHUN = re.compile(r"eumhun(?:\s+reading)?:?\s+((?:[가-힣]+\s+)+?)([가-힣])\s*\(")
GLOSS = re.compile(r"hanja form\??\s+of\s+[가-힣]+\s*\(“([^”]+)”\)")


def eumhun_from_text(text):
    """Reads the 훈음 from Wiktionary's displayed text, e.g. '(eumhun 가을 추 (ga'eul chu))'."""
    hun = eum = en = ""
    m = EUMHUN.search(text)
    if m:
        hun, eum = m.group(1).strip(), m.group(2)
    g = GLOSS.search(text)
    if g:
        en = g.group(1).strip()[:60]
    return {"hun": hun, "eum": eum, "en": en}


def char_hunum(c):
    r = get("https://en.wiktionary.org/w/api.php", params={
        "action": "parse", "page": c, "prop": "text", "format": "json", "formatversion": "2", "redirects": "1"})
    j = r.json()
    if "error" in j:
        return {"hun": "", "eum": "", "en": ""}
    html_text = j["parse"]["text"]
    text = clean(html_text.split('id="Korean"', 1)[1] if 'id="Korean"' in html_text else html_text)
    return eumhun_from_text(text)


def need_lookup(cache, ch):
    e = cache.get(ch)
    return not e or not e.get("hun")


# ---------- 4. stories ----------
STORY_PROMPT = """You write short graded Korean reading passages for an adult learner who studies the way
Korean schoolchildren do (hanja-aware). Today's trending topics in Korea: {topics}
Today's new words (word, hanja, English, learner level):
{words}

Write TWO original short stories inspired by today's topics. They must be fiction or everyday
scenes, never a copy or summary of a news article, and avoid naming real living people.
1. level "easy": 6-8 sentences, beginner grammar (polite -아요/어요, simple past), using 2-4 of the
   easier words above.
2. level "hard": 8-10 sentences, intermediate grammar (-아서, -지만, -는데, -(으)면), using 5-8 of the
   words above.

Return ONLY a JSON object, no markdown fences:
{{"stories":[{{"level":"easy","title":"Korean title","en":"English title",
 "lines":[["Korean sentence","natural English translation"]],
 "vocab":[["word as it appears in dictionary form","standard Korean hanja or empty string for native words","English"]],
 "quiz":[{{"q":"question in Korean","qen":"the question in English","opts":["","","",""],"a":0}}]}}]}}
Each story: 6-12 vocab items including the words used; hanja must be accurate standard Korean hanja
and line up syllable-for-character with the word (use "" if the word is native or mixed).
Exactly 4 quiz questions per story: 3 on understanding the story, 1 on a word's meaning or hanja.
"a" is the index (0-3) of the correct option; vary its position."""


def valid_story(st):
    ok_lines = [l for l in st.get("lines", []) if isinstance(l, list) and len(l) == 2 and all(isinstance(x, str) for x in l)]
    quiz = [q for q in st.get("quiz", []) if isinstance(q, dict) and isinstance(q.get("opts"), list)
            and len(q["opts"]) == 4 and isinstance(q.get("a"), int) and 0 <= q["a"] < 4]
    vocab = [v for v in st.get("vocab", []) if isinstance(v, list) and len(v) == 3 and all(isinstance(x, str) for x in v)]
    for v in vocab:  # keep hanja only if it lines up with the syllables (하다 verbs: the part before 하다)
        stem = v[0][:-2] if v[0].endswith("하다") else v[0]
        v[1] = only_hanja(v[1], v[0]) or only_hanja(v[1], stem)
    return ok_lines, vocab, quiz


def claude_stories(chosen, topics):
    if not ANTHROPIC_KEY or not chosen:
        return []
    words = "\n".join(f"- {w['ko']} | {w['hanja'] or '-'} | {w['en']} | {w['grade'] or '?'}" for w in chosen)
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=180, headers={
        "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": ANTHROPIC_MODEL, "max_tokens": 6000, "messages": [
            {"role": "user", "content": STORY_PROMPT.format(topics=", ".join(topics[:8]) or "(none)", words=words)}]})
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json().get("content", []))
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0)) if m else {}
    out = []
    for st in data.get("stories", []):
        lines, vocab, quiz = valid_story(st)
        if len(lines) < 4:
            continue
        out.append({"title": str(st.get("title", ""))[:60], "en": str(st.get("en", ""))[:80],
                    "lvl": 2 if st.get("level") == "easy" else 4, "lines": lines, "vocab": vocab, "quiz": quiz})
    return out


def wiki_story(topics, wiki, lookup, chosen):
    """Fallback: the opening of a trending topic's Korean Wikipedia article (CC BY-SA)."""
    for title in [t for t in topics if len(t) <= 15] + wiki[:15]:
        try:
            j = get("https://ko.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"))).json()
        except Exception:
            continue
        if j.get("type") != "standard":
            continue
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", j.get("extract", "")) if 6 <= len(x.strip()) <= 140][:6]
        if len(sents) < 3:
            continue
        text = " ".join(sents)
        vocab = [[w["ko"], w["hanja"], w["en"]] for w in chosen if w["ko"] in text]
        # add a few more words from the passage itself
        from kiwipiepy import Kiwi
        extra = [t.form for t in Kiwi().tokenize(text) if t.tag == "NNG" and len(t.form) >= 2]
        for w in dict.fromkeys(extra):
            if len(vocab) >= 10:
                break
            if any(v[0] == w for v in vocab):
                continue
            try:
                info = lookup(w)
            except Exception:
                info = None
            time.sleep(0.25)
            if info:
                vocab.append([w, info["hanja"], info["en"]])
        return {"title": j.get("title", title), "en": "", "lvl": 4,
                "lines": [[x, ""] for x in sents], "vocab": vocab, "quiz": [],
                "source": j.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "license": "Text from Korean Wikipedia, CC BY-SA 4.0"}
    return None


def with_chars(story, cache):
    chars = []
    for v in story["vocab"]:
        for ch in v[1]:
            if need_lookup(cache, ch):
                try:
                    cache[ch] = char_hunum(ch)
                except Exception:
                    cache[ch] = {"hun": "", "eum": "", "en": ""}
                time.sleep(0.25)
            if ch not in [c["c"] for c in chars]:
                chars.append({"c": ch, **{k: cache[ch].get(k, "") for k in ("hun", "eum", "en")}})
    story["chars"] = chars
    return story


# ---------- 5. subject words ----------
# Each subject reads one Korean Wikipedia article a day, starting from these seeds and then
# following links from articles it has read, so the vocabulary keeps growing within the field.
SUBJECT_SEEDS = {
    "math": ["수학", "대수학", "기하학", "미적분학", "확률론", "통계학", "정수론", "선형대수학", "집합론", "삼각법",
             "함수", "방정식", "수열", "행렬", "소수 (수론)", "피타고라스 정리", "로그 (수학)", "극한"],
    "science": ["물리학", "화학", "생물학", "지구과학", "천문학", "원자", "세포", "진화", "열역학", "전자기학",
                "광합성", "유전학", "화학 반응", "행성", "지진", "뉴턴 운동 법칙", "주기율표", "생태계"],
    "engineering": ["공학", "기계공학", "전기공학", "토목공학", "건축학", "재료공학", "반도체", "로봇공학", "제어공학",
                    "자동화", "전자공학", "화학공학", "교량", "내연기관", "전기 회로", "신재생 에너지", "항공우주공학"],
    "business": ["경제학", "경영학", "주식", "금융", "무역", "회계", "마케팅", "인플레이션", "중앙은행", "기업",
                 "투자", "시장 경제", "국내총생산", "환율", "세금", "스타트업", "공급망"],
    "culture": ["한국의 문화", "국악", "판소리", "한복", "한옥", "김치", "태권도", "한국 영화", "서예", "민속놀이",
                "한국 문학", "한국의 대중음악", "탈춤", "사물놀이", "한국의 차 문화", "무형문화재", "미술"],
    "philosophy": ["철학", "유교", "불교", "윤리학", "형이상학", "인식론", "논리학", "실존주의", "성리학", "도가",
                   "공리주의", "미학", "자유 의지", "정의", "소크라테스", "공자", "맹자", "칸트"],
    "history": ["한국사", "고조선", "삼국 시대", "고려", "조선", "세종", "임진왜란", "대한제국", "일제강점기",
                "한국 전쟁", "신라", "백제", "고구려", "발해", "3·1 운동", "산업 혁명", "로마 제국"],
    "medicine": ["의학", "면역계", "감염병", "심장", "뇌", "혈액", "영양", "당뇨병", "고혈압", "백신", "외과학",
                 "약리학", "정신 건강", "암", "감기", "소화계", "호흡계", "공중보건"],
}


def wiki_article(title):
    """Plain text (first ~8000 characters) and linked article titles of a Korean Wikipedia page."""
    j = get("https://ko.wikipedia.org/w/api.php", params={
        "action": "query", "prop": "extracts|links", "explaintext": "1", "titles": title, "redirects": "1",
        "plnamespace": "0", "pllimit": "60", "format": "json", "formatversion": "2"}).json()
    pages = j.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return "", []
    pg = pages[0]
    return (pg.get("extract") or "")[:8000], [l["title"] for l in pg.get("links", [])]


def subject_words(state, skip, lookup, cache, per_subject):
    """Returns {subject: [word, ...]} and updates the crawl state."""
    from kiwipiepy import Kiwi
    kiwi = Kiwi()
    out = {}
    for key, seeds in SUBJECT_SEEDS.items():
        st = state.setdefault(key, {"queue": list(seeds), "read": []})
        st["queue"] += [t for t in seeds if t not in st["queue"] and t not in st["read"]]
        words = []
        for _ in range(3):  # try up to three articles to find enough new words
            if len(words) >= per_subject or not st["queue"]:
                break
            title = st["queue"].pop(0)
            st["read"].append(title)
            try:
                text, links = wiki_article(title)
            except Exception as e:
                log("  wikipedia failed:", title, e)
                continue
            # follow links, but keep the seed list ahead of them so the subject doesn't drift
            st["queue"] += [l for l in links[:20] if l not in st["read"] and l not in st["queue"] and ":" not in l]
            st["queue"] = st["queue"][:300]
            count = collections.Counter()
            sentence = {}
            for sent in re.split(r"(?<=[.!?])\s+", text):
                for tok in kiwi.tokenize(sent):
                    w = tok.form
                    if tok.tag != "NNG" or len(w) < 2 or not HANGUL.match(w) or w in STOP or w in skip:
                        continue
                    count[w] += 1
                    if w not in sentence and 10 <= len(sent) <= 90:
                        sentence[w] = sent.strip()
            for w, n in count.most_common(40):
                if len(words) >= per_subject:
                    break
                if n < 2 or any(x["ko"] == w for x in words):
                    continue
                try:
                    info = lookup(w)
                except Exception:
                    info = None
                time.sleep(0.25)
                if not info or not info["hanja"]:   # subject vocabulary: Sino-Korean terms only
                    continue
                chars = []
                for ch in info["hanja"]:
                    if need_lookup(cache, ch):
                        try:
                            cache[ch] = char_hunum(ch)
                        except Exception:
                            cache[ch] = {"hun": "", "eum": "", "en": ""}
                        time.sleep(0.25)
                    chars.append({"c": ch, **{k: cache[ch].get(k, "") for k in ("hun", "eum", "en")}})
                words.append({"ko": w, "hanja": info["hanja"], "en": info["en"], "grade": info["grade"],
                              "example": sentence.get(w, ""), "source": title, "chars": chars})
                skip.add(w)
        out[key] = words
        log(f"  {key}: " + ", ".join(f"{x['ko']} {x['hanja']}" for x in words))
    return out


# ---------- 6. assemble the day ----------
def build(day, out, per_day, keep_days, per_subject=3):
    out.mkdir(parents=True, exist_ok=True)
    words_path, hist_path, cache_path = out / "words.json", out / "history.json", out / "hunum_cache.json"
    subj_path = out / "subjects_state.json"
    subj_state = json.loads(subj_path.read_text()) if subj_path.exists() else {}
    data = json.loads(words_path.read_text()) if words_path.exists() else {"days": []}
    history = set(json.loads(hist_path.read_text())) if hist_path.exists() else set()
    cache = json.loads((HERE / "hunum_seed.json").read_text())
    if cache_path.exists():
        cache.update(json.loads(cache_path.read_text()))
    base = set(json.loads((HERE / "base_vocab.json").read_text()))

    log(f"{day}: collecting")
    trends, news, wiki, topics = collect(day)
    cands, example = candidates(trends, news, wiki, skip=base | history)
    log(f"  {len(cands)} candidates")

    lookup = krdict if KRDICT_KEY else wiktionary
    chosen, native = [], 0
    for w in cands[:per_day * 5]:
        if len(chosen) >= per_day:
            break
        try:
            info = lookup(w)
        except Exception as e:
            log("  lookup failed:", w, e)
            info = None
        time.sleep(0.25)
        if not info:
            continue
        if not info["hanja"]:
            if native >= per_day // 3:   # keep the focus on words with characters
                continue
            native += 1
        chars = []
        for ch in info["hanja"]:
            if need_lookup(cache, ch):
                try:
                    cache[ch] = char_hunum(ch)
                except Exception:
                    cache[ch] = {"hun": "", "eum": "", "en": ""}
                time.sleep(0.25)
            chars.append({"c": ch, **{k: cache[ch].get(k, "") for k in ("hun", "eum", "en")}})
        chosen.append({"ko": w, **info, "example": example.get(w, ""), "chars": chars})
        log(f"  + {w} {info['hanja']} {info['grade']} — {info['en'][:40]}")

    stories = []
    try:
        stories = claude_stories(chosen, topics)
        log(f"  {len(stories)} stories written")
    except Exception as e:
        log("  story writing failed:", e)
    if not stories:
        ws = wiki_story(topics, wiki, lookup, chosen)
        if ws:
            stories = [ws]
            log("  story from Wikipedia:", ws["title"])
    stories = [with_chars(st, cache) for st in stories]

    log("  subjects:")
    skip_subj = base | history | {c["ko"] for c in chosen}
    subjects = subject_words(subj_state, skip_subj, lookup, cache, per_subject)

    days = [d for d in data["days"] if d["date"] != day.isoformat()]
    days.append({"date": day.isoformat(), "topics": topics, "words": chosen, "stories": stories, "subjects": subjects})
    days = sorted(days, key=lambda d: d["date"])[-keep_days:]
    # Fill in 훈음 on earlier days that were saved while a lookup was failing
    for d in days:
        for item in d.get("words", []) + d.get("stories", []) + [w for ws in d.get("subjects", {}).values() for w in ws]:
            for c in item.get("chars", []):
                if not c.get("hun") and cache.get(c["c"], {}).get("hun"):
                    c.update({k: cache[c["c"]].get(k, "") for k in ("hun", "eum", "en")})
    words_path.write_text(json.dumps({"generated": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                                      "days": days}, ensure_ascii=False, indent=1))
    new_subject_words = {w["ko"] for ws in subjects.values() for w in ws}
    hist_path.write_text(json.dumps(sorted(history | {c["ko"] for c in chosen} | new_subject_words), ensure_ascii=False))
    subj_path.write_text(json.dumps(subj_state, ensure_ascii=False))
    cache_path.write_text(json.dumps(cache, ensure_ascii=False))
    log(f"  wrote {len(chosen)} words")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--per-day", type=int, default=15)
    ap.add_argument("--keep-days", type=int, default=30)
    ap.add_argument("--per-subject", type=int, default=3, help="new words per subject per day")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in Korea)")
    a = ap.parse_args()
    kst = dt.timezone(dt.timedelta(hours=9))
    day = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(kst).date()
    build(day, Path(a.out), a.per_day, a.keep_days, a.per_subject)
