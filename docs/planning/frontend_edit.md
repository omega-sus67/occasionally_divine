# Frontend Edit — Giving *Occasionally Divine* a Pixelated Feel

> **How to use this doc:** I've laid out the decisions as a series of forks. Under each,
> edit the `**DECISION →**` line with your call (or notes/questions). We iterate until
> every decision is locked, then I implement. Nothing here is built yet.

---

## 0. The core tension (read this first)

Your current design — "Majestic Paranoia" — is **already good and internally consistent**:

- Painterly / cinematic: soft gold glows, violet mysticism, film grain, vignette, an
  animated atmosphere canvas.
- Serif typography built for *reading*: Cinzel (carved display) + Merriweather (long
  narrative body). This game is **text-heavy** — the situation narrative is 4-6 sentences
  the player actually reads every turn.

Pixel art is a **different language**: hard edges, limited palette, nearest-neighbor
scaling, dithering instead of soft gradients, and (usually) bitmap fonts. These two
aesthetics *fight each other* if mixed carelessly — soft glow + hard pixel edge reads as
"unfinished," not "stylish."

So the real decision is **not** "make it pixelated." It's:

> **How much** of the pixel language do we adopt, and **which parts** of the UI wear it —
> without wrecking readability or blowing the July 5 deadline?

There are three coherent destinations. Pick one as the target (we can always dial between
them).

---

## 1. THE BIG FORK — how far do we go?

### Option A — "Pixel Accents" (hybrid, lowest risk) — ✅ **DECIDED, in progress**
Keep the painterly base and typography. Introduce pixel *texture* only in decorative
elements: a pixel-art shrine sprite, pixel icons for stats/elders, dithered borders,
pixel-corner panels. Body text stays Merriweather (readable).

- **Pros:** Low risk, keeps readability, ~1 day, preserves the polish you already have.
- **Cons:** It's "painterly game with pixel bits," not "a pixel game." Less of a wow-flip.

**Implementation approach:** CSS-only (route 1 from §4) — no sprite assets, no asset-pack
dependency. Baked directly into `styles.css` as accents (not a separate toggle theme,
since this is additive by nature and doesn't replace the existing look).

Concrete accents being applied:
1. Pixel UI font (Silkscreen) for stat labels/values, mana value, badges, buttons — narrative body stays Merriweather.
2. Segmented/blocky fill on stat bars, dread meter, mana orb (CSS `repeating-linear-gradient`, no assets).
3. Stepped "pixel corner" panel borders via `clip-path` polygon, applied to key panels/cards.
4. Tapestry of Fate node cards get pixel-frame treatment.
5. `image-rendering: pixelated` on any raster/canvas elements where it helps crispness.

### Option B — "Pixel Diorama + Readable Chrome" (recommended middle)
Commit the *visual/spatial* layer to pixel art — the shrine, the kingdom diorama/tiles,
elder portraits, weather, icons all become sprites with `image-rendering: pixelated`.
The *UI chrome* (panels, buttons, meters) goes blocky/pixel-framed with a pixel **UI**
font (e.g. for labels, numbers, buttons). **Long narrative body text stays a readable
font** (Merriweather or a cleaner pixel-friendly serif) so the story is still legible.

- **Pros:** Reads unmistakably as "a pixel game" where it counts (the world, the icons),
  keeps the novel-length text readable, strong demo/hackathon flip. ~2 days.
- **Cons:** Requires actual sprite assets (see §4). Mixed-font discipline needed.

### Option C — "Full Pixel / Retro" (highest risk)
Everything pixel: bitmap font *including* narrative body, pixel panels, pixel everything,
CRT scanline overlay, 8/16-bit palette. Think a SNES strategy game.

- **Pros:** Maximum aesthetic commitment, most memorable.
- **Cons:** Bitmap fonts hurt long-form reading badly; you'd likely have to *shorten*
  narratives. Highest asset load. Riskiest to finish well by July 5. Easy to land in
  "amateur" rather than "retro-cool."

**DECISION → _(A / B / C, or describe your own blend)_:**
_..._

---

## 2. TYPOGRAPHY (the single most important pixel decision for a text game)

Pixel/bitmap fonts and 4-6 sentence narratives are natural enemies. Options:

| Choice | Narrative body | UI labels / numbers / buttons | Titles |
|---|---|---|---|
| **T1** Keep all current fonts | Merriweather | Inter | Cinzel |
| **T2** Pixel chrome, readable body *(pairs with B)* | Merriweather (or readable serif) | Pixel font (e.g. "Silkscreen"/"Pixelify Sans"/"VT323") | Pixel display font |
| **T3** Full bitmap *(pairs with C)* | Pixel font | Pixel font | Pixel font |

Candidate pixel fonts (Google Fonts, free): **Silkscreen** (tiny/crisp UI), **Pixelify
Sans** (friendly, has weights), **VT323** (terminal/CRT), **Press Start 2P** (chunky,
poor for long text). "Jersey"/"Micro 5" are other options.

- Trade-off to weigh: the more pixel the body text, the shorter narratives must become to
  stay readable. That's a *content* change, not just CSS.

**DECISION → _(T1 / T2 / T3 + which pixel font)_:**
_..._

---

## 3. COMPONENT-BY-COMPONENT — what actually changes

Here's every real piece of the current UI and what "pixelated" would mean for each.
Mark **keep / pixelate / redesign** per row (defaults reflect Option B).

| Component | Current | Under pixel treatment | Your call |
|---|---|---|---|
| Background atmosphere (`atmosphere.js` canvas) | smooth particles/weather | pixel snow/rain/embers, dithered fog | _pixelate?_ |
| Grain + vignette overlays | film grain, soft vignette | swap for dither/scanline overlay? | _keep / swap?_ |
| Mana orb (top-left) | CSS gradient orb + glow | pixel orb sprite, stepped fill | _pixelate?_ |
| Stat ribbon (5 meters) | smooth gradient bars | segmented/blocky "heart-container" style bars | _pixelate?_ |
| Shrine emblem (center, SVG) | injected SVG, upgrades by level | **pixel shrine sprite per level** (wooden→stone→cathedral) | _pixelate?_ |
| Dread/unrest meter | gradient fill | segmented pixel meter | _pixelate?_ |
| Elder council (left cards) | text cards + mood | **pixel elder portraits** w/ mood frames | _portraits?_ |
| Situation modal (narrative) | serif text block | keep readable; pixel frame around it | _keep body readable?_ |
| Intervention cards | styled buttons | pixel-bordered cards, icon per type (bless/nudge/wrath/wait) | _pixelate?_ |
| Chronicle / Adaptations / Whispers (right) | text lists | pixel bullet icons, blocky frames | _pixelate frames?_ |
| Tapestry of Fate (tree modal) | CSS connector tree | pixel node cards + blocky connectors (could be gorgeous) | _pixelate?_ |
| Oracle / Dossier / Lore modals | styled panels | pixel window frames | _pixelate?_ |
| Spectacle FX (miracle/smite flash) | glow flashes | pixel burst / screen-shake / palette flash | _pixelate?_ |
| Color palette (`:root` tokens) | 30+ soft hex values | quantize to a tighter retro palette? | _requantize?_ |

**Notes / overrides →**
_..._

---

## 4. ASSETS — where do the sprites come from? (the real constraint)

Option B/C need actual pixel art (shrine, tiles, elder portraits, icons). This is the part
that can't be pure CSS. Four sourcing routes:

1. **CSS-only pixel look** — hard edges, pixel fonts, `box-shadow` pixel icons, dithered
   gradients. *No sprite files.* Gets ~60% of the feel for icons/borders, but **cannot**
   give you a real pixel shrine/diorama. Cheapest, fastest, safest for the deadline.
2. **Free asset packs** — itch.io / Kenney.nl have CC0 medieval pixel tilesets, characters,
   UI kits. Fast, high quality, but generic; must match palette.
3. **AI-generated pixel art** — generate shrine/portraits/icons, hand-clean. Fast, custom,
   but consistency/quality is a gamble and may need touch-up.
4. **Hand-drawn** — you (or a teammate) draw in Aseprite/Piskel. Best fit, slowest, needs
   the skill.

Given July 5, I'd lean **1 for chrome/icons + 2 for the hero sprites (shrine, elders)**,
palette-matched.

**DECISION → _(which sourcing route(s), and do you already have any assets?)_:**
_..._

---

## 5. TECHNICAL APPROACH (how I'd build it — for reference, not a decision unless you care)

- Global `image-rendering: pixelated;` on sprite `<img>`/canvas so scaled art stays crisp.
- Introduce a **pixel scale unit** (e.g. everything snaps to 4px grid) and blocky borders
  via `border-image` or layered `box-shadow` (no anti-aliasing).
- Add pixel fonts via Google Fonts `<link>` (same mechanism as current fonts).
- Keep the existing token system in `:root`; add/quantize a retro palette alongside so we
  can A/B without ripping out everything.
- Do it as an **additive theme layer** first (a `body.pixel` class / `pixel.css`) so we can
  toggle and compare against the current look instead of a destructive rewrite. Lower risk,
  easy to demo both.
- Keep all the backend-driven DOM IDs/structure intact — this is purely a
  CSS/asset/markup-wrapper pass, no logic changes.

**Any technical constraints/preferences →**
_..._

---

## 6. SCOPE vs DEADLINE (honest)

- **Option A:** ~0.5-1 day. Safe.
- **Option B:** ~2 days *if* assets come from packs (route 2) rather than hand-drawn.
  Realistic and high-impact for a hackathon demo. This is my recommendation.
- **Option C:** 2.5-3+ days and content rewrites (shorter narratives). Risky this close to
  the deadline; only if pixel-everything is the whole point of your pitch.

Given you also still want a README + demo GIF before submission, **B with a toggleable
pixel theme** gives the best wow-per-hour without betting the whole deadline.

---

## 7. MY RECOMMENDATION (for you to accept / override)

- **§1:** Option **B** — pixel world + readable chrome.
- **§2:** **T2** — Merriweather body, **Silkscreen** (or Pixelify Sans) for UI/labels,
  pixel display font for titles.
- **§4:** CSS-only for borders/icons + one free medieval pack for shrine & elder portraits.
- **§5:** Build as a toggleable `body.pixel` theme layer so we never lose the current look.
- Highest-impact pixel targets to do *first* (biggest visual payoff): **shrine sprite**,
  **elder portraits**, **stat/dread meters → segmented**, **Tapestry tree → pixel nodes**.

**Your overall verdict / changes →**
_..._

---

## 8. OPEN QUESTIONS FOR YOU

1. Is this a *replace* the current look, or a *toggleable alternate* theme? (I recommend
   toggleable.)
2. Do you have any pixel assets already, or an artist on the team?
3. Any reference games/screenshots whose pixel vibe you want to match? (Drop links/paths.)
4. Is shortening the narrative text acceptable if we go more pixel (Option C)?
5. Anything currently in the UI you *dislike* and want changed while we're in here anyway?

**Answers →**
_..._
