#!/usr/bin/env python3
"""
Cozy Smart Mama Hub (single-file, standard-library web app)

A gentle, educational, fun “reprieve” homepage for:
- new mothers (safe, supportive, non-judgmental tone)
- cat households
- very-smart software engineering / DevOps survivors
- Totoro-ish cozy vibes + daily challenges + “this day” style content

Run:
  python cozy_mama_hub.py
Open:
  http://127.0.0.1:8000

Notes:
- This is NOT medical advice. It includes a simple resources footer.
- “Today in history” tries Wikimedia’s On This Day feed if online, and falls back to built-in fun facts.
- Everything is contained in this one file.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import http.server
import json
import socketserver
import textwrap
import urllib.request
import urllib.error
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8000


# -----------------------------
# Content (safe + cozy + smart)
# -----------------------------

NEW_MOM_TIPS = [
    "If you did one small kind thing for yourself today (water, snack, shower, a 2-minute stretch), that counts as winning.",
    "Sleep isn’t a moral issue. Any rest you get is valid. If you can, trade naps like a pager rotation: one on, one off.",
    "If you feel overwhelmed, shrink the scope: ‘next 10 minutes’ instead of ‘the whole day.’",
    "Feeding the baby is the goal. The method is personal. You’re allowed to choose what works for your family.",
    "A crying baby is not a failing parent. It’s a tiny human communicating with the tools they have.",
    "If visitors add work, you’re allowed to say: ‘We’d love help—could you bring food or fold laundry?’",
    "Gentle reminder: you don’t need to ‘bounce back.’ You’re not an app rollback. You’re a human.",
    "Try the ‘minimum viable routine’: one anchor you can usually do (tea, sunlight, a short walk, a playlist).",
]

DEVOPS_FACTS = [
    "Blameless postmortems work because they optimize for learning, not punishment—systems fail; humans adapt.",
    "Idempotency is self-care for infrastructure: running it twice shouldn’t make things worse.",
    "Good alerts are actionable. If it can’t be acted on, it’s probably noise (and noise steals rest).",
    "SLOs are empathy tools: they set expectations so teams (and parents) aren’t living in permanent ‘SEV-1.’",
    "The fastest incident response is often: reduce scope, restore service, then investigate. Same with hard nights.",
    "Backpressure is a kindness: it protects downstream systems—like saying ‘not today’ to extra commitments.",
    "‘You build it, you run it’ is powerful—until burnout. Sustainable on-call is a feature, not a luxury.",
]

# Cozy “Totoro-style” prompts: vibe-forward, not claiming any official association.
COZY_ANIME_VIBES = [
    "Forest spirit moment: notice one tiny detail (steam from tea, warm socks, the sound of rain).",
    "Soft animation rule: slow down one scene today. You don’t have to time-lapse your life.",
    "Kindness quest: send one simple message to someone you trust: ‘Could use a little encouragement today.’",
    "Tiny heroism: do one small helpful task that future-you will thank you for (refill water, prep a snack).",
    "Gentle magic: open a window for 60 seconds. Fresh air counts as a reset.",
    "Cozy soundtrack: play one calming song and breathe with it—no productivity required.",
]

POWER_COUPLE_CHALLENGES = [
    {
        "title": "The 7-Minute Hand-Off",
        "why": "Reduce friction + keep teamwork alive.",
        "steps": [
            "One person gets 7 minutes completely off-duty (no questions).",
            "Other person handles the immediate need (baby/cat/laundry/whatever).",
            "Switch. Celebrate the swap like a successful deploy.",
        ],
    },
    {
        "title": "Two-Truths Status Update",
        "why": "Stay connected without a long talk.",
        "steps": [
            "Each share: (1) one hard thing, (2) one good/neutral thing.",
            "No fixing—just ‘heard you.’",
            "Optional: one tiny ask (‘Could you refill bottles?’).",
        ],
    },
    {
        "title": "Incident Command Lite",
        "why": "When everything’s on fire, roles help.",
        "steps": [
            "Pick roles for 20 minutes: IC (decides), Operator (does), Scribe (notes).",
            "Define goal: ‘Everyone fed + back to bed.’",
            "After: 30-second retro—one thing that worked.",
        ],
    },
]

CAT_CORNER = [
    "Cat pro-tip: put a soft blanket in a ‘cat-approved’ spot near where you feed/rock baby—cats love being included without being on top of you.",
    "If the litter box smell suddenly changes, it might be time for a deeper clean—or a quick vet check if behavior changes. (Trust your instincts.)",
    "A scratching post near the high-traffic baby zone can redirect stress scratching into something positive.",
    "Keep dangling strings/ribbons out of reach—cats + tired humans + small objects is a chaos combo.",
]

LOCAL_FUN_FACTS = [
    "Honey never spoils—archaeologists have tasted ancient honey found in tombs.",
    "Octopuses have three hearts and blue blood.",
    "Bananas are berries, but strawberries aren’t (botany is a menace).",
    "The dot over an ‘i’ or ‘j’ is called a ‘tittle.’",
    "Cats have fewer taste receptors for sweetness than humans do.",
    "The first computer ‘bug’ was famously a moth found in a relay.",
]

KIND_REMINDERS = [
    "You are not behind. You are living through a high-demand season.",
    "Your worth is not measured in output, cleanliness, or inbox zero.",
    "Asking for help is senior-level engineering: it’s resource management.",
    "You can be brilliant and exhausted at the same time.",
]


# -----------------------------
# Helpers
# -----------------------------

def _seed_for_date(d: _dt.date) -> int:
    h = hashlib.sha256(d.isoformat().encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def pick_daily(items: list[str], d: _dt.date) -> str:
    if not items:
        return ""
    idx = _seed_for_date(d) % len(items)
    return items[idx]

def pick_daily_obj(items: list[dict], d: _dt.date) -> dict:
    if not items:
        return {}
    idx = _seed_for_date(d) % len(items)
    return items[idx]

def try_fetch_wikimedia_onthisday(d: _dt.date, timeout_s: float = 2.0) -> dict | None:
    """
    Wikimedia 'On this day' feed:
      https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/MM/DD
    Returns parsed JSON dict or None on failure.
    """
    mm = str(d.month)
    dd = str(d.day)
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{mm}/{dd}"
    req = urllib.request.Request(
        url,
        headers={
            # A UA helps some endpoints behave nicely.
            "User-Agent": "CozySmartMamaHub/1.0 (single-file python demo)"
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            if resp.status != 200:
                return None
            data = resp.read()
        return json.loads(data.decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

def summarize_onthisday(payload: dict) -> list[dict]:
    """
    Turn Wikimedia payload into a small list of safe, readable bullets.
    """
    out: list[dict] = []
    if not isinstance(payload, dict):
        return out

    # Common keys: "events", "births", "deaths", "holidays", "selected"
    events = payload.get("events") or []
    births = payload.get("births") or []

    def pick_top(items, n=3):
        cleaned = []
        for it in items:
            if not isinstance(it, dict):
                continue
            year = it.get("year")
            text = it.get("text") or ""
            if text:
                cleaned.append({"year": year, "text": text})
        return cleaned[:n]

    for e in pick_top(events, 3):
        out.append({"kind": "event", **e})
    for b in pick_top(births, 2):
        out.append({"kind": "birth", **b})

    return out


def build_day_data(today: _dt.date) -> dict:
    tip = pick_daily(NEW_MOM_TIPS, today)
    devops = pick_daily(DEVOPS_FACTS, today)
    vibe = pick_daily(COZY_ANIME_VIBES, today)
    cat = pick_daily(CAT_CORNER, today)
    reminder = pick_daily(KIND_REMINDERS, today)
    challenge = pick_daily_obj(POWER_COUPLE_CHALLENGES, today)
    fun_fact = pick_daily(LOCAL_FUN_FACTS, today)

    onthisday = []
    src = "local"
    wiki_payload = try_fetch_wikimedia_onthisday(today)
    if wiki_payload:
        onthisday = summarize_onthisday(wiki_payload)
        if onthisday:
            src = "wikimedia"

    return {
        "date": today.isoformat(),
        "safe_disclaimer": "This page is for comfort + education only, not medical advice. If you’re worried about your health or safety, contact a clinician or local emergency number.",
        "new_mom_tip": tip,
        "devops_fact": devops,
        "anime_vibe": vibe,
        "cat_corner": cat,
        "kind_reminder": reminder,
        "power_couple_challenge": challenge,
        "fun_fact": fun_fact,
        "on_this_day": onthisday,
        "on_this_day_source": src,
    }


def html_page() -> str:
    # Keep the HTML fully static; JS calls /api/daydata for dynamic content.
    # Everything is “safe” and avoids medical claims.
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cozy Smart Mama Hub</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: rgba(255,255,255,0.08);
      --panel2: rgba(255,255,255,0.06);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.72);
      --soft: rgba(255,255,255,0.14);
      --line: rgba(255,255,255,0.12);
      --good: rgba(180,255,214,0.95);
      --warn: rgba(255,227,180,0.95);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      background:
        radial-gradient(1000px 600px at 10% 10%, rgba(120,170,255,0.25), transparent 60%),
        radial-gradient(900px 600px at 80% 20%, rgba(140,255,200,0.18), transparent 55%),
        radial-gradient(800px 600px at 50% 90%, rgba(255,210,140,0.14), transparent 60%),
        var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 22px 16px 56px;
    }}
    .top {{
      display: flex;
      gap: 14px;
      align-items: stretch;
      justify-content: space-between;
      flex-wrap: wrap;
    }}
    .hero {{
      flex: 1 1 520px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.06));
      border-radius: 18px;
      padding: 18px 18px 14px;
      position: relative;
      overflow: hidden;
    }}
    .hero:before {{
      content: "";
      position: absolute;
      inset: -80px -120px auto auto;
      width: 280px;
      height: 280px;
      background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.22), transparent 55%);
      transform: rotate(18deg);
      filter: blur(1px);
    }}
    h1 {{
      margin: 0 0 8px 0;
      font-weight: 800;
      letter-spacing: 0.2px;
      font-size: clamp(22px, 3.2vw, 34px);
    }}
    .sub {{
      margin: 0;
      color: var(--muted);
      line-height: 1.35;
      max-width: 70ch;
    }}
    .pillrow {{
      margin-top: 14px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .pill {{
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.18);
      padding: 7px 10px;
      border-radius: 999px;
      color: var(--muted);
      font-size: 13px;
    }}
    .rightbox {{
      flex: 1 1 340px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.06);
      border-radius: 18px;
      padding: 16px;
    }}
    .date {{
      display:flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .date .d1 {{
      font-weight: 800;
      font-size: 16px;
    }}
    .date .d2 {{
      color: var(--muted);
      font-size: 13px;
    }}
    .mini {{
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.16);
      border-radius: 14px;
      padding: 12px;
    }}
    .mini h3 {{
      margin: 0 0 8px 0;
      font-size: 14px;
      letter-spacing: 0.2px;
    }}
    .mini p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.35;
      font-size: 13px;
    }}

    .grid {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 12px;
    }}
    .card {{
      grid-column: span 6;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 18px;
      padding: 14px;
    }}
    .card.big {{ grid-column: span 12; }}
    .card.three {{ grid-column: span 4; }}
    @media (max-width: 920px) {{
      .card.three {{ grid-column: span 6; }}
    }}
    @media (max-width: 680px) {{
      .card {{ grid-column: span 12; }}
      .card.three {{ grid-column: span 12; }}
    }}
    .card h2 {{
      margin: 0 0 8px 0;
      font-size: 16px;
      letter-spacing: 0.2px;
    }}
    .card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .kicker {{
      display:flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
      align-items: baseline;
    }}
    .tag {{
      font-size: 12px;
      color: var(--muted);
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.16);
      padding: 3px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }}
    .list {{
      margin: 10px 0 0 0;
      padding-left: 18px;
      color: var(--muted);
    }}
    .list li {{ margin: 6px 0; line-height: 1.35; }}
    .row {{
      display:flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 10px;
      align-items: center;
    }}
    button {{
      cursor: pointer;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.18);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 12px;
      font-weight: 700;
    }}
    button:hover {{
      background: rgba(255,255,255,0.10);
    }}
    .ghost {{
      color: var(--muted);
      font-weight: 700;
    }}
    .check {{
      display:flex;
      gap: 10px;
      align-items: center;
      padding: 10px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.14);
      margin-top: 10px;
    }}
    input[type="checkbox"] {{
      width: 18px;
      height: 18px;
      accent-color: rgba(160,240,210,0.95);
    }}
    .footer {{
      margin-top: 16px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      border-top: 1px solid var(--line);
      padding-top: 14px;
    }}
    .hr {{
      height: 1px;
      background: var(--line);
      margin: 10px 0;
    }}
    .tiny {{
      font-size: 12px;
      color: var(--muted);
    }}
    .good {{
      color: var(--good);
      font-weight: 800;
    }}
    .warn {{
      color: var(--warn);
      font-weight: 800;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 12px;
    }}
  </style>
</head>

<body>
  <div class="wrap">
    <div class="top">
      <section class="hero">
        <h1>Cozy Smart Mama Hub</h1>
        <p class="sub">
          A calm, supportive corner for new moms (and their cats) who also happen to be frighteningly competent engineers.
          No guilt. No hustle. Just gentle tools, tiny challenges, and cozy vibes.
        </p>
        <div class="pillrow">
          <span class="pill">🌿 soft-focus energy</span>
          <span class="pill">🐾 cat-friendly home</span>
          <span class="pill">🧠 engineer brain welcomed</span>
          <span class="pill">🛠️ DevOps survivor humor</span>
        </div>
      </section>

      <aside class="rightbox">
        <div class="date">
          <div class="d1" id="todayLabel">Today</div>
          <div class="d2" id="sourceLabel"></div>
        </div>

        <div class="mini">
          <h3>Quick reset (60 seconds)</h3>
          <p id="resetText">Inhale 4 · hold 2 · exhale 6 — repeat for one minute. You’re not behind; you’re in a high-demand season.</p>
          <div class="row">
            <button id="startTimerBtn">Start 60s timer</button>
            <span class="tiny" id="timerStatus"></span>
          </div>
        </div>

        <div class="check">
          <input id="checkboxDone" type="checkbox" />
          <label for="checkboxDone">
            Today I did <span class="good">one</span> kind thing for myself.
            <span class="tiny">(Counts: water, snack, stretch, sunlight, asking for help.)</span>
          </label>
        </div>
      </aside>
    </div>

    <div class="grid">
      <section class="card">
        <div class="kicker">
          <h2>🍼 New-mom tip of the day</h2>
          <span class="tag">gentle + practical</span>
        </div>
        <p id="momTip"></p>
      </section>

      <section class="card">
        <div class="kicker">
          <h2>🛠️ Fact of the day for former DevOps survivors</h2>
          <span class="tag mono">SRE-ish wisdom</span>
        </div>
        <p id="devopsFact"></p>
      </section>

      <section class="card three">
        <div class="kicker">
          <h2>🐾 Cat corner</h2>
          <span class="tag">tiny chaos manager</span>
        </div>
        <p id="catCorner"></p>
      </section>

      <section class="card three">
        <div class="kicker">
          <h2>🌱 Kind reminder</h2>
          <span class="tag">no guilt</span>
        </div>
        <p id="kindReminder"></p>
      </section>

      <section class="card three">
        <div class="kicker">
          <h2>🎲 Random fun fact</h2>
          <span class="tag">brain candy</span>
        </div>
        <p id="funFact"></p>
      </section>

      <section class="card big">
        <div class="kicker">
          <h2>🍃 “Totoro-style” anime vibe prompt</h2>
          <span class="tag">cozy moment</span>
        </div>
        <p id="animeVibe"></p>
        <div class="hr"></div>
        <div class="kicker">
          <h2>👩‍❤️‍👨 Power couple micro-challenge</h2>
          <span class="tag">2–7 minutes</span>
        </div>
        <p class="tiny" id="challengeWhy"></p>
        <ul class="list" id="challengeSteps"></ul>

        <div class="row">
          <button id="markChallengeBtn">Mark as done</button>
          <span class="tiny" id="challengeStatus"></span>
        </div>
      </section>

      <section class="card big">
        <div class="kicker">
          <h2>📅 Today in history</h2>
          <span class="tag" id="historyTag">local fallback</span>
        </div>
        <p class="tiny">
          This tries to fetch Wikimedia’s “On this day” feed when you’re online. If it fails, you’ll still get a cozy fallback.
        </p>
        <ul class="list" id="historyList"></ul>
        <p class="tiny mono" id="historySourceNote"></p>
      </section>

      <section class="card big">
        <div class="kicker">
          <h2>🧩 Engineer brain: tiny “choose your own difficulty” challenge</h2>
          <span class="tag">optional</span>
        </div>
        <p class="tiny">Pick one. If you’re exhausted, choose <span class="good">Level 0</span> and call it a victory.</p>
        <ul class="list">
          <li><span class="good">Level 0:</span> write a 1-sentence log line: <span class="mono">"Today was hard because ___ . One good thing was ___ ."</span></li>
          <li><span class="good">Level 1:</span> do a 2-minute tidy sprint (set a timer, stop when it ends).</li>
          <li><span class="good">Level 2:</span> refactor one tiny household “process” (where do wipes live? where does laundry start?).</li>
          <li><span class="good">Level 3:</span> add one small automation (calendar reminder, grocery list shortcut, bottle prep checklist).</li>
        </ul>
      </section>
    </div>

    <div class="footer">
      <div class="warn">Not medical advice.</div>
      <div>
        If you’re concerned about postpartum mood, anxiety, intrusive thoughts, or safety, you deserve real support.
        In the U.S., you can call/text <span class="mono">988</span> for the Suicide &amp; Crisis Lifeline.
        If you feel in immediate danger, call your local emergency number.
      </div>
      <div class="hr"></div>
      <div class="tiny">
        This page stores only two tiny toggles in your browser (checkbox + challenge done), using <span class="mono">localStorage</span>.
      </div>
    </div>
  </div>

<script>
  async function loadDayData() {{
    const res = await fetch('/api/daydata');
    const data = await res.json();

    // Date label
    const d = new Date(data.date + "T00:00:00");
    const fmt = new Intl.DateTimeFormat(undefined, {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }});
    document.getElementById('todayLabel').textContent = fmt.format(d);

    // Cards
    document.getElementById('momTip').textContent = data.new_mom_tip;
    document.getElementById('devopsFact').textContent = data.devops_fact;
    document.getElementById('animeVibe').textContent = data.anime_vibe;
    document.getElementById('catCorner').textContent = data.cat_corner;
    document.getElementById('kindReminder').textContent = data.kind_reminder;
    document.getElementById('funFact').textContent = data.fun_fact;

    // Challenge
    document.getElementById('challengeWhy').textContent = "Why: " + data.power_couple_challenge.why;
    const steps = document.getElementById('challengeSteps');
    steps.innerHTML = "";
    for (const s of data.power_couple_challenge.steps) {{
      const li = document.createElement('li');
      li.textContent = s;
      steps.appendChild(li);
    }}

    // History
    const tag = document.getElementById('historyTag');
    const list = document.getElementById('historyList');
    const note = document.getElementById('historySourceNote');
    list.innerHTML = "";

    if (data.on_this_day && data.on_this_day.length) {{
      tag.textContent = data.on_this_day_source === "wikimedia" ? "Wikimedia feed" : "history";
      for (const it of data.on_this_day) {{
        const li = document.createElement('li');
        const yr = it.year ? (it.year + " — ") : "";
        li.textContent = yr + it.text;
        list.appendChild(li);
      }}
      note.textContent = data.on_this_day_source === "wikimedia"
        ? "source: api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all"
        : "";
    }} else {{
      tag.textContent = "local fallback";
      const li1 = document.createElement('li');
      li1.textContent = "Today’s theme: tiny wins count (especially the invisible ones).";
      const li2 = document.createElement('li');
      li2.textContent = "If you want: take one photo of something peaceful today (steam, window light, cat loaf).";
      const li3 = document.createElement('li');
      li3.textContent = "Engineer note: your system is under peak load. Reduce scope, protect rest, accept ‘good enough.’";
      list.append(li1, li2, li3);
      note.textContent = "history feed unavailable; showing cozy fallback";
    }}

    // Source label (subtle)
    document.getElementById('sourceLabel').textContent =
      data.on_this_day_source === "wikimedia" ? "online: Wikimedia history feed" : "offline-friendly mode";
  }}

  // LocalStorage state
  const LS_DONE = "cozyhub_done_checkbox";
  const LS_CHAL = "cozyhub_challenge_done";
  function loadLocalState() {{
    const cb = document.getElementById('checkboxDone');
    cb.checked = localStorage.getItem(LS_DONE) === "1";
    cb.addEventListener('change', () => {{
      localStorage.setItem(LS_DONE, cb.checked ? "1" : "0");
    }});

    const chalDone = localStorage.getItem(LS_CHAL) === "1";
    document.getElementById('challengeStatus').textContent =
      chalDone ? "✅ Logged. Proud of you." : "Not logged yet.";
  }}

  document.getElementById('markChallengeBtn').addEventListener('click', () => {{
    localStorage.setItem(LS_CHAL, "1");
    document.getElementById('challengeStatus').textContent = "✅ Logged. Proud of you.";
  }});

  // 60s timer
  let timer = null;
  document.getElementById('startTimerBtn').addEventListener('click', () => {{
    if (timer) return;
    const status = document.getElementById('timerStatus');
    let remaining = 60;
    status.textContent = "60s…";
    timer = setInterval(() => {{
      remaining -= 1;
      status.textContent = remaining > 0 ? (remaining + "s…") : "Done. That counted.";
      if (remaining <= 0) {{
        clearInterval(timer);
        timer = null;
        setTimeout(() => status.textContent = "", 3000);
      }}
    }}, 1000);
  }});

  (async function init() {{
    loadLocalState();
    await loadDayData();
  }})();
</script>
</body>
</html>
"""


# -----------------------------
# HTTP server
# -----------------------------

class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            page = html_page().encode("utf-8")
            return self._send(200, page, "text/html; charset=utf-8")

        if path == "/api/daydata":
            today = _dt.date.today()
            data = build_day_data(today)
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            return self._send(200, body, "application/json; charset=utf-8")

        # simple health
        if path == "/health":
            return self._send(200, b"ok\n", "text/plain; charset=utf-8")

        return self._send(404, b"Not found\n", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        # Quiet logs (comment out to enable request logging)
        return


def main():
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"Cozy Smart Mama Hub running at http://{HOST}:{PORT}")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
