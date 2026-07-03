# Dynamic Atmosphere System — Design Plan

> The player should never need to read a stat to understand the state of their kingdom. 
> They should *feel* it the moment the screen loads.

---

## The Core Problem

Right now, whether the kingdom is starving under a Blood Moon or thriving on a clear summer day, the screen looks identical: dark brown, static, silent. The backend already tracks `kingdom.weather` (Clear | Rain | Storm | Drought | Fog) and `kingdom.omen_active` (Blood Moon | Comet | Eclipse | None), but the frontend does absolutely nothing with this data. 

We need to make the screen a living mirror of the kingdom's state.

---

## System 1: Weather Layer (CSS Background + Particle Canvas)

The idea: A full-screen `<canvas>` element sits behind all UI content. Based on the current `weather` value from the backend, we draw different particle effects onto this canvas.

### Weather States

| Weather | Background Color Shift | Particle Effect | Notes |
|---------|----------------------|-----------------|-------|
| **Clear** | Default (`#241711`) | Gentle floating dust motes (warm amber dots, slow drift) | Calm, peaceful. The "resting" state. |
| **Rain** | Cooler, darker (`#1a1a24`) | Diagonal blue-white streaks falling rapidly | Should feel heavy and melancholic. |
| **Storm** | Very dark (`#0d0d15`) + periodic white flashes | Rain streaks + occasional full-screen white flash (lightning) | Screen should feel dangerous. Add CSS `animation: screenShake` on lightning. |
| **Drought** | Warm sepia shift (`#2e1e0a`) | Slow-rising heat shimmer particles (tiny orange dots drifting upward) | Oppressive. The UI itself should feel dry and cracked. |
| **Fog** | Washed out, low contrast (`#2a2520` with reduced text opacity) | Large, slow-moving translucent white blobs drifting across | Eerie. Reduces visibility of the UI itself slightly, creating unease. |

### Implementation

1. Add a `<canvas id="atmosphere-canvas">` behind the `.app-container` in `index.html`.
2. Create a new file `frontend/atmosphere.js` dedicated to the particle engine.
3. The canvas uses `requestAnimationFrame` for a simple particle loop.
4. Export a function `setWeather(weatherType)` that switches the active particle set.
5. On each game state update from the backend, call `setWeather(kingdomState.weather)`.

### Particle Engine (Simple Design)

```
class Particle:
    x, y           — position
    vx, vy         — velocity
    size           — radius
    opacity        — alpha
    color          — hex string

ParticlePool:
    particles[]    — array of active Particles
    spawnRate      — how many new particles per frame
    
    update():
        for each particle:
            move by velocity
            reduce opacity (fade out)
            if off-screen or invisible: recycle
        spawn new particles based on spawnRate
    
    draw(ctx):
        for each particle:
            ctx.fillStyle = particle.color with particle.opacity
            ctx.fillRect or ctx.arc
```

Each weather type defines a different `ParticleConfig` object:
- `rain`: `{ color: '#a0b4d4', vy: 12, vx: -3, size: 1.5, spawnRate: 15 }`
- `drought`: `{ color: '#d4884a', vy: -0.5, vx: 0.2, size: 2, spawnRate: 3 }`
- `fog`: `{ color: '#ffffff', vy: 0, vx: 0.3, size: 40, opacity: 0.04, spawnRate: 1 }`
- `clear`: `{ color: '#c9a96e', vy: -0.2, vx: 0.1, size: 1, spawnRate: 1 }` (dust motes)

---

## System 2: Omen Overlays (CSS Filters + Animated Vignettes)

Omens are rare, dramatic events. They should feel *terrifying* or *awe-inspiring*.

### Omen States

| Omen | Visual Effect | CSS Approach |
|------|--------------|--------------|
| **Blood Moon** | The entire screen shifts to a deep red tint. A dark red radial vignette pulses slowly at the edges. | `filter: hue-rotate(-30deg) saturate(1.5)` on `body` + a pulsing `box-shadow: inset` red vignette on `.app-container`. |
| **Comet** | A bright streak slowly arcs across the top of the canvas over ~30 seconds, trailing golden particles. | Draw a single bright particle with a long trail on the `atmosphere-canvas`. The rest of the UI gets a slight golden tint. |
| **Eclipse** | The screen dramatically darkens. A dark circular shadow creeps inward from the edges. Text becomes harder to read. | `filter: brightness(0.4)` + a radial gradient overlay that simulates the shadow. Text gets `text-shadow: 0 0 8px white` to remain legible. |
| **None** | No overlay. Standard state. | Remove all filters and overlays. |

### Implementation

1. Add a `<div id="omen-overlay">` after the canvas layer.
2. CSS classes: `.omen-blood-moon`, `.omen-comet`, `.omen-eclipse`.
3. A function `setOmen(omenType)` toggles the correct class on the overlay div and triggers the canvas-level effects (e.g., comet trail).

---

## System 3: Stat-Driven Visual Tension (Reactive UI Chrome)

The UI borders and backgrounds should shift color based on critical stat thresholds. The player should sense danger without reading a number.

### Trigger Rules

| Condition | Visual Effect |
|-----------|--------------|
| `food < 30` | The stat bar for food pulses red. A faint red vignette appears at the bottom of the screen (starvation creeping in). |
| `unrest > 70` | The `.app-container` border flickers between `var(--border-medium)` and a harsh orange. Subtle CSS `animation: flicker` on the border. |
| `faith > 80` | Golden particles drift upward from the bottom (divine devotion). The shrine stat glows with a warm aura. |
| `morale < 20` | The text color desaturates slightly (`filter: saturate(0.7)` on `.main-content`). Everything looks drained and hopeless. |
| `trust < 20` | A paranoia effect: the edges of the screen get a slight static/noise overlay. The people don't trust you. |

### Implementation

1. After each game state update, run a `updateTensionEffects(stats)` function.
2. This function applies/removes CSS classes to specific elements.
3. All effects are purely CSS-driven (keyframe animations, filters, box-shadows). No extra canvas work needed.

---

## System 4: Intervention Spectacle (Divine Action Feedback)

When the player clicks a divine action, there should be a brief, dramatic full-screen animation before the results are shown.

### Action Types

| Action Type | Animation |
|-------------|-----------|
| **Benevolent Miracle** (e.g., "Summon Rain") | Screen flashes a soft blue-white. Golden particles burst outward from the center. Fades after 1.5s. |
| **Subtle Nudge** (e.g., "Whisper to the Elders") | A gentle ripple effect (CSS radial gradient that expands from center). Fades after 1s. |
| **Wrathful/Evil Action** (e.g., "Smite the Village") | Screen goes pure white for 200ms, then cracks appear (a CSS overlay image of cracked glass), then fades to the darkened result. Screen shakes for 500ms. |
| **Do Nothing** | No animation. The silence itself is the feedback. |

### Implementation

1. Create a `<div id="spectacle-overlay">` on top of everything (z-index: 9999).
2. A function `playSpectacle(type)` applies the correct CSS animation class and removes it after the duration.
3. CSS keyframes for `@keyframes flash`, `@keyframes ripple`, `@keyframes crack`, `@keyframes screenShake`.

---

## System 5: Ambient Sound (Optional, High Impact)

Not visual, but massively impactful for immersion.

| State | Sound |
|-------|-------|
| Clear weather | Gentle wind, birdsong |
| Rain | Rain ambience |
| Storm | Thunder rumbles, heavy rain |
| Blood Moon | Low, ominous drone |
| High Faith | Distant chanting |
| Low Food | Faint crying/wailing |

### Implementation
- Use the Web Audio API or simple `<audio>` tags.
- Store small `.mp3` loops in a `frontend/audio/` directory.
- Cross-fade between ambient tracks when weather/omen changes.

---

## File Architecture

```
frontend/
├── index.html          (add <canvas>, overlay divs)
├── styles.css          (add omen classes, tension animations, spectacle keyframes)
├── app.js              (call atmosphere/spectacle functions on state updates)
├── atmosphere.js       [NEW] (particle engine, weather/omen management)
└── audio/              [NEW, OPTIONAL] (ambient sound loops)
```

---

## Priority Order (What to Build First)

1. **Weather Particles** — Highest impact, most visible change. The screen immediately feels alive.
2. **Omen Overlays** — Dramatic, rare, and cheap to implement (mostly CSS).
3. **Intervention Spectacle** — Makes every player action feel powerful.
4. **Stat-Driven Tension** — Adds passive urgency without any player action needed.
5. **Ambient Sound** — Last because it requires sourcing audio assets.

---

## Estimated Effort

| System | Complexity | Time |
|--------|-----------|------|
| Weather Particles | Medium (canvas + particle loop) | ~45 min |
| Omen Overlays | Low (CSS classes + filters) | ~20 min |
| Intervention Spectacle | Medium (CSS keyframes + JS timing) | ~30 min |
| Stat-Driven Tension | Low (CSS classes + threshold checks) | ~20 min |
| Ambient Sound | Low-Medium (audio API + asset sourcing) | ~30 min |
| **Total** | | **~2.5 hours** |

---

## Summary

The goal is simple: **the screen should be a window into the kingdom, not a spreadsheet about it.** Every weather change, every omen, every famine and miracle should be *felt* before it is read. The backend already generates all this data — we just need to paint it.
