// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-blue; icon-glyph: language;

/*
 * 한빛 학당 — word of the day for the iPhone lock screen.
 * 1. Change SITE below to your GitHub Pages address (keep the slash at the end).
 * 2. Name this script exactly: Hanbit
 * 3. Add a Scriptable widget to your lock screen and pick this script.
 */
const SITE = "https://YOUR-NAME.github.io/hanbit/";

const fm = FileManager.local();
const dir = fm.joinPath(fm.documentsDirectory(), "hanbit");
if (!fm.fileExists(dir)) fm.createDirectory(dir);
const P = n => fm.joinPath(dir, n);

function readJSON(file, fallback) {
  try { return fm.fileExists(P(file)) ? JSON.parse(fm.readString(P(file))) : fallback; }
  catch (e) { return fallback; }
}
async function loadJSON(url, file) {
  try {
    const r = new Request(url);
    r.timeoutInterval = 15;
    const j = await r.loadJSON();
    fm.writeString(P(file), JSON.stringify(j));
    return j;
  } catch (e) {
    return readJSON(file, null);   // offline: use the last copy
  }
}

// Opened from the app's "Send my progress" button: remember the learner's level
const q = args.queryParameters || {};
if (q.state) fm.writeString(P("state.json"), q.state);

const state = readJSON("state.json", { learned: 0, known: [] });
const daily = (await loadJSON(SITE + "data/words.json", "words.json")) || { days: [] };
const baseRaw = await loadJSON(SITE + "base_words.json", "base.json");
const base = Array.isArray(baseRaw) ? baseRaw : [];

// ---- same rule as the app, so both show the same word ----
const pad = n => String(n).padStart(2, "0");
const d = new Date();
const day = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
function jhash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0; return h & 0x7fffffff; }
const hunumOf = w => (w.chars || []).map(c => `${c.hun || ""} ${c.eum || ""}`.trim()).join(" · ");

const lookup = new Map();
base.forEach(w => lookup.set(w.ko + "|" + w.hanja, w));
(daily.days || []).forEach(dd => (dd.words || []).forEach(w =>
  lookup.set(w.ko + "|" + (w.hanja || ""), { ko: w.ko, hanja: w.hanja || "", en: w.en || "", hunum: hunumOf(w) })));

function pick() {
  const learned = state.learned || 0, known = state.known || [], h = jhash(day);
  const kset = new Set(known.map(k => k[0]));
  const prefer = learned < 300 ? ["초급", ""] : learned < 900 ? ["중급", "초급", ""] : ["고급", "중급", "초급", ""];
  const days = daily.days || [];
  const latest = days.length ? (days[days.length - 1].words || []) : [];
  if (!(known.length >= 20 && h % 3 === 0)) {
    const fresh = latest.filter(w => !kset.has(w.ko) && w.hanja);
    for (const g of prefer) {
      const f = fresh.find(w => (w.grade || "") === g);
      if (f) return { ko: f.ko, hanja: f.hanja, en: f.en || "", hunum: hunumOf(f), isNew: true };
    }
  }
  if (known.length) {
    const k = known[h % known.length], w = lookup.get(k[0] + "|" + k[1]);
    if (w) return w;
  }
  return base.length ? base[h % base.length] : { ko: "학교", hanja: "學校", en: "school", hunum: "배울 학 · 학교 교" };
}
const word = pick();

// ---- draw ----
const serif = size => new Font("AppleMyungjo", size);
const fam = config.widgetFamily;
const w = new ListWidget();

if (fam === "accessoryInline") {
  w.addText(`${word.ko} ${word.hanja} · ${word.en}`);
} else if (fam === "accessoryCircular") {
  w.addAccessoryWidgetBackground = true;
  const t = w.addText(word.hanja ? [...word.hanja][0] : word.ko);
  t.font = serif(24); t.centerAlignText(); t.minimumScaleFactor = 0.5;
  const s = w.addText(word.ko);
  s.font = Font.semiboldSystemFont(10); s.centerAlignText(); s.minimumScaleFactor = 0.6;
} else if (fam === "accessoryRectangular") {
  const row = w.addStack(); row.bottomAlignContent();
  const k = row.addText(word.ko); k.font = Font.boldSystemFont(17); k.lineLimit = 1;
  row.addSpacer(6);
  const hj = row.addText(word.hanja); hj.font = serif(14); hj.lineLimit = 1;
  const hu = w.addText(word.hunum || ""); hu.font = Font.systemFont(12); hu.lineLimit = 1; hu.minimumScaleFactor = 0.7;
  const en = w.addText(word.en); en.font = Font.systemFont(12); en.lineLimit = 1; en.textOpacity = 0.8;
} else {
  // Home screen (small/medium) and the in-app preview
  const g = new LinearGradient();
  g.colors = [new Color("#22384A"), new Color("#121820")]; g.locations = [0, 1];
  w.backgroundGradient = g; w.setPadding(14, 16, 14, 16);
  const tag = w.addText(word.isNew ? "오늘의 새 단어" : "오늘의 단어");
  tag.font = Font.systemFont(11); tag.textColor = new Color("#E2B236");
  w.addSpacer(4);
  const row = w.addStack(); row.bottomAlignContent();
  const k = row.addText(word.ko); k.font = Font.boldSystemFont(30); k.textColor = Color.white(); k.minimumScaleFactor = 0.6;
  row.addSpacer(8);
  const hj = row.addText(word.hanja); hj.font = serif(22); hj.textColor = new Color("#CFE3DA"); hj.minimumScaleFactor = 0.6;
  const hu = w.addText(word.hunum || ""); hu.font = Font.systemFont(14); hu.textColor = new Color("#E6EDE8");
  const en = w.addText(word.en); en.font = Font.systemFont(13); en.textColor = new Color("#B8C6D0"); en.lineLimit = 2;
}

// Check again in a few hours (and just after midnight for the new word)
const midnight = new Date(); midnight.setHours(24, 1, 0, 0);
w.refreshAfterDate = new Date(Math.min(Date.now() + 3 * 3600e3, midnight.getTime()));

if (config.runsInWidget) {
  Script.setWidget(w);
} else {
  if (q.state) {
    const a = new Alert();
    a.title = "Widget updated";
    a.message = `${state.learned || 0} items learned. The lock-screen word will match your level at its next refresh.`;
    a.addAction("OK");
    await a.present();
  }
  await w.presentMedium();
}
Script.complete();
