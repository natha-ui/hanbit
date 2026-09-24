#!/usr/bin/env python3
"""
한빛 학당 — daily words pipeline.

Collects what Korea is talking about today (Google Trends, news RSS, most-read
Korean Wikipedia pages), finds the words that keep coming up, looks up their
hanja and English, and adds the 훈음 (meaning + sound) of every character.
Writes data/words.json, which the phone app downloads each morning.

Dictionary: set KRDICT_KEY (free key from krdict.korean.go.kr/openApi) for
learner-graded words (초급/중급/고급). Without it, English Wiktionary is used.

    python pipeline/daily_words.py --out data
"""
import argparse, collections, datetime as dt, html, json, os, re, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

HERE = Path(__file__).parent
UA = {"User-Agent": "HanbitHakdang/0.2 (personal Korean study project)"}
KRDICT_KEY = os.environ.get("KRDICT_KEY", "").strip()

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


def char_hunum(c):
    sec = wikt_korean(c)
    hun = eum = en = ""
    m = re.search(r"eumhun\s*=\s*" + PARAM, sec) or \
        re.search(r"\{\{ko-hanja-reading\|" + re.escape(c) + r"\|" + PARAM, sec)
    if m:
        parts = strip_wiki(m.group(1)).split()
        if len(parts) >= 2:
            hun, eum = " ".join(parts[:-1]), parts[-1]
    m2 = re.search(r"\{\{ko-hanja-reading\|" + re.escape(c) + r"\|" + PARAM + r"\|" + PARAM, sec)
    if m2:
        en = strip_wiki(m2.group(2))[:60]
    return {"hun": hun, "eum": eum, "en": en}


# ---------- 4. assemble the day ----------
def build(day, out, per_day, keep_days):
    out.mkdir(parents=True, exist_ok=True)
    words_path, hist_path, cache_path = out / "words.json", out / "history.json", out / "hunum_cache.json"
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
            if ch not in cache:
                try:
                    cache[ch] = char_hunum(ch)
                except Exception:
                    cache[ch] = {"hun": "", "eum": "", "en": ""}
                time.sleep(0.25)
            chars.append({"c": ch, **{k: cache[ch].get(k, "") for k in ("hun", "eum", "en")}})
        chosen.append({"ko": w, **info, "example": example.get(w, ""), "chars": chars})
        log(f"  + {w} {info['hanja']} {info['grade']} — {info['en'][:40]}")

    days = [d for d in data["days"] if d["date"] != day.isoformat()]
    days.append({"date": day.isoformat(), "topics": topics, "words": chosen})
    days = sorted(days, key=lambda d: d["date"])[-keep_days:]
    words_path.write_text(json.dumps({"generated": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                                      "days": days}, ensure_ascii=False, indent=1))
    hist_path.write_text(json.dumps(sorted(history | {c["ko"] for c in chosen}), ensure_ascii=False))
    cache_path.write_text(json.dumps(cache, ensure_ascii=False))
    log(f"  wrote {len(chosen)} words")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--per-day", type=int, default=15)
    ap.add_argument("--keep-days", type=int, default=30)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in Korea)")
    a = ap.parse_args()
    kst = dt.timezone(dt.timedelta(hours=9))
    day = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(kst).date()
    build(day, Path(a.out), a.per_day, a.keep_days)
