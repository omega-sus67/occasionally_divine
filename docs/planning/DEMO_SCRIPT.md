# Demo Script — Occasionally Divine

*For the Cognee "Hangover Part AI" hackathon submission. Two cuts: a **100-second core cut** (use this one — judges stop watching, not you) and an **optional extended cut** (~2:40) if the submission form allows a longer video and you want the Council + Oracle beats too.*

---

## Before you record

**Read this section — it will save you a bad take.**

1. **There is no seed save.** The README/old script referenced `backend/demo_seed.db`, but it was never actually committed — `.gitignore` reserves the filename but the file doesn't exist. You are recording a **real, live playthrough**, not a curated save. That's fine — it's more honest anyway, and every beat below is now reliably reachable in a short, real session because of this session's fixes:
   - Council of Elders now convenes at **Unrest ≥ 70** (it was silently checking `≥ 100` *after* passive drift capped it at 97 — mathematically unreachable before). It will fire for real if you push unrest up.
   - Causal chaining (the `⟴ CONSEQUENCE` badge) now fires on **~65% of turns**, with a **guaranteed chain** after any severity-4+ situation. You will not have to wait long or re-record for this.
   - The post-turn chronicle now types out with a **Proceed** button — no more auto-dismissing text you can't read on camera.
   - The next situation now **prefetches while you're reading the chronicle**, so the loading veil mostly disappears — turns feel instant on camera.

2. **Decide: fresh kingdom or your current save.** Check what you've got:
   ```bash
   cd backend && venv/bin/python3 -c "
   import sqlite3
   c = sqlite3.connect('occasionally_divine.db').cursor()
   c.execute('SELECT current_year, current_season, realm_unrest, faith, food, game_status FROM kingdoms LIMIT 1')
   print(c.fetchone())
   "
   ```
   - If `food` or `faith` is near 0, or `game_status` isn't `active`, **reset** (title screen → New Game, or `POST /reset`) rather than risk an on-camera defeat mid-recording.
   - If you want a chain/adaptation-rich kingdom *and* are willing to spend a few real turns of LLM budget before recording, play forward off-camera first, then record from a good moment. Either way, **practice the run once before you hit record** so you know your own beats.

3. **To reliably hit the Council beat on camera:** pick the wrathful (evil, negative-cost) intervention 2–3 turns in a row. It generates Mana *and* spikes Unrest — fastest path to 70. Don't do this as your very first recorded turn, or the tone whiplash reads oddly; let one or two normal turns establish the world first.

4. **Recording setup:**
   - `cp backend/occasionally_divine.db backend/occasionally_divine.db.bak` first if you care about preserving the current save.
   - Backend running: `cd backend && venv/bin/uvicorn main:app --port 8000`
   - Open `http://localhost:8000` full-screen, bookmarks bar hidden.
   - Do one throwaway turn first (uncounted) so fonts, atmosphere canvas, and API latency are warmed up and you know the rhythm.
   - Record at 1080p+. A voiceover reading the lines below out loud, live, lands better than subtitles — the game's own narrative voice is dry and wry, so read your lines the same way: understated, not hyped.

---

## THE CORE CUT (~100 seconds)

Say the pitch line over the very first shot, before anything else loads:

> **"This is Occasionally Divine — a god-game where the kingdom is powered by a Cognee knowledge graph, so it remembers everything you do to it. Not as flavor text — mechanically."**

### Shot 1 — The living kingdom (0:00–0:12)
**Do:** Land on the main screen mid-game (not the title screen). Let it breathe for 3–4 seconds — don't click anything. Slowly hover across the five elder cards.
**Say:** *"Five elders with persistent moods and grudges, a rumor mill, a living chronicle — stored twice: SQL for what the kingdom **is**, a Cognee graph for what it's **been through**."*
**Why it scores:** establishes stakes + Technical Excellence (dual-memory architecture) in one breath, before any UI explanation is needed.

### Shot 2 — A crisis with a memory (0:12–0:38)
**Do:** Point the cursor at the `⟴ CONSEQUENCE · born of …` badge on the active situation.
**Say:** *"This crisis isn't random — it was caused by something I did two seasons ago. The engine retrieved that from the graph and linked it."*
**Do:** Click **Echoes of the Past** to expand the retrieved-memories panel. Scroll it slowly — let a couple of lines actually be readable on camera.
**Say:** *"And here's the receipts. The exact memories Cognee retrieved to write this scene — not vibes, auditable retrieval."*
**Why it scores:** this is the single best 20 seconds for **Best Use of Cognee** — it's the moment judges see the graph, not just hear about it.
**Fallback:** if this generation has no badge, click through one more turn — at ~65% odds (100% after any severity-4+ crisis) it won't take long. Note the Echoes panel hides itself entirely when there's genuinely nothing retrieved yet (e.g. turn 1, before the graph has anything in it) — don't record this beat on your very first turn of the session.

### Shot 3 — The Tapestry (0:38–0:50)
**Do:** Click the CONSEQUENCE badge (or the **Tapestry of Fate** button) to open the causal tree. Hover a node or two, click one open.
**Say:** *"Every playthrough grows its own causal tree. This is the kingdom's memory, and you can walk it."*
**Why it scores:** Creativity/Innovation — nothing else at this hackathon will look like this.

### Shot 4 — Choose an intervention, and watch it cost something (0:50–1:20)
**Do:** Close the Tapestry. Pick an intervention — ideally the **wrathful** one (the spectacle flash is the most dramatic, and it's one of three random variants per type, so it won't look identical to last time). Let the spectacle FX play, then the chronicle type out.
**Say (over the flash):** *"Choices write back into the graph as structured memories — not raw text, typed Pydantic facts the graph can actually reason over."*
**Do:** Let the chronicle finish typing, then click **Proceed** yourself — don't rush it, this is the one moment on screen built for the player (and the judge) to actually read.
**If the "Kingdom Remembers" banner fires** (an adaptation matching this crisis category already exists): linger on it for the full sentence.
**Say (if it fires):** *"And when the Council builds an adaptation, it isn't flavor text — seasons later the graph remembers what it was built for, and it **mechanically** halves the damage. No trusting the model to remember; the code checks."*
**Why it scores:** Technical Excellence + Best Use of Cognee, back to back — retrieval feeding generation, then mechanically enforced by code, not by prompt-and-hope.

### Shot 5 — Close (1:20–1:40)
**Do:** Back on the main screen as the next situation is already rendering (thanks to the prefetch, there's little to no loading veil here — that's worth letting play out naturally rather than cutting past it).
**Say:** *"SQL remembers what the kingdom is. Cognee remembers what it's been through. The game is what happens when the second one talks back."*
**Cut.**

---

## EXTENDED CUT — add these two beats if your submission allows a longer video

*(Check the hackathon submission form for any stated video-length limit before assuming these fit — insert after Shot 4, before Shot 5.)*

### Shot 4b — The Council convenes (+40s)
**Do:** Once Unrest crosses 70 (see prep step 3), the Council overlay opens automatically. Let one or two debate lines stream in — pause on an angry one (screen shake fires).
**Say:** *"When unrest boils over, the Council convenes for real now — and they're not generic. They pull grudges and past votes straight out of the graph before they argue."*
**Do:** Let the decree reveal, stamp it.
**Say:** *"Their decision becomes a permanent adaptation — a real object in the graph, not a line of dialogue that evaporates."*
**Why it scores:** this was the mechanic most likely to be missing from other teams' recordings because it was *unreachable* before this session's fix — showing it working is a quiet flex.

### Shot 4c — Ask the Oracle (+30s)
**Do:** Click **Consult Oracle**. Type a real question about something that actually happened in this playthrough — e.g. an elder's name, or the title of an earlier crisis you saw in Shot 2/3. Let the answer stream in.
**Say:** *"You can just ask it things. The Oracle answers purely from what's retrieved from the graph — and if the graph doesn't know, it says so instead of making something up."*
**Why it scores:** the most judge-interactive beat in the whole demo — suggest they imagine asking their own question. Grounded honesty (the "Tapestry is silent" fallback) is a stronger signal than a lucky hit would be.
**Tip:** ask about something you *know* is in the graph (an elder, a crisis title on screen) so the first live answer isn't the awkward "silent" case — save that admission for the voiceover, not the demo.

---

## If you're recording for social / open-source tracks too

- Tag **@wemakedevs** and the official Cognee account on any blog or social post — required for those tracks, easy to forget mid-scramble.
- The pitch line and Shot 2's line ("not vibes, auditable retrieval") both double as good post captions.

## Trim guide

- **Under 60s (teaser only):** Shots 1 → 2 → 5. Cut the Tapestry and the intervention entirely; it's still a complete, honest pitch.
- **~100s (recommended core cut):** Shots 1–5 as written above.
- **~2:40 (extended):** Core cut + 4b (Council) + 4c (Oracle).

## Fallbacks (keep these in mind, don't panic)

- If a generation is slow on camera, cut the wait in editing — never leave more than ~2s of loading veil in the final cut (and with the prefetch fix, most turns won't need any).
- If the current save is close to a defeat state, reset before recording rather than gambling on a mid-take game-over.
- If Council or CONSEQUENCE hasn't fired yet when you meant to record that beat, that's fine — play one more real turn. These are no longer rare edge cases; they're normal turns now.
