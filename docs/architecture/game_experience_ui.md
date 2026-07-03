# Occasionally Divine: Game Experience & UI/UX Vision

*Occasionally Divine* is a narrative-driven God Simulator where abstract stats and deep-history graph data manifest through character-driven storytelling and high-impact visual feedback. Because the heavy lifting of causality, grudges, and memory is handled by the Cognee backend, the UI must focus entirely on **dopamine hits, immersion, and making the player feel the weight of their choices.**

This document outlines the complete player experience and the specific UI elements required to bring the simulation to life.

---

## 1. Aesthetic Direction: "Majestic Paranoia"

The UI should not feel like a spreadsheet. It should feel like you are looking down at a living diorama. 
*   **Art Style**: High-fidelity pixel art mixed with smooth, modern CSS micro-animations.
*   **Color Palette**: Deep mystical purples and golds (Divine power), offset by harsh, gritty earth tones (the mortal realm). When Unrest is high or Omens are active, the palette should shift to sickly reds and oppressive greys.
*   **Typography**: Elegant serif fonts for narrative text (giving a biblical/historical feel), and clean sans-serif for UI numbers.

---

## 2. Core Game Loop Experience

The game progresses in "Seasons". The loop flows seamlessly between three distinct views:

### A. The God's Eye View (Main Dashboard)
This is the default view where the player watches the consequences of their actions unfold.

**UI Elements:**
*   **The Centerpiece (The Shrine)**: The physical anchor of the game. It occupies the center of the screen as a detailed pixel-art sprite. 
    *   *Visual Feedback*: It upgrades visually (Wooden Altar -> Stone Temple -> Cathedral). If Unrest is high, torches and angry silhouettes appear at its base. If weather changes (Rain, Fog), particle effects overlay the shrine.
*   **The Divine Economy (Top Bar)**:
    *   **Divine Influence (Mana)**: A large, glowing orb. When full, it radiates light. When empty, it crackles weakly.
    *   **Mortal Stats (Food, Faith, Unrest)**: Clean, sleek progress bars. **Dopamine Hit:** When stats change, the numbers should roll up/down dramatically, with positive changes glowing gold and negative changes flashing crimson.
*   **The Whispers of the Realm (Right Panel)**:
    *   A scrolling list of `Active Rumors`. If a rumor involves the `SuspectDivineMemory` (Paranoia), the text should have a subtle, unsettling glitch effect to warn the player that they are being investigated.
*   **The Chronicle (Left Panel)**: 
    *   A beautifully formatted scroll showing past events and adaptations.

### B. The Crisis Modal (The Situation Engine)
When the LLM generates a new Situation, the game pauses, and a dramatic modal overtakes the screen.

**UI Elements:**
*   **The Narrative Frame**: The situation title and evocative narrative are displayed like a page in an ancient book. The text types out dynamically (typewriter effect) to force the player to read the flavor text.
*   **The Intervention Cards**: The 4 choices are presented as beautifully illustrated tarot-style cards. 
    *   *Visual Feedback*: 
        *   **Benevolent Miracles** emit a soft, holy glow. Hovering over them shows a negative Mana cost (drains power).
        *   **Wrathful Miracles** (Blood sacrifices, plagues) emit a dark, sinister smoke effect. Hovering shows a positive Mana cost (fuels power). 
        *   **The Click**: Selecting a card should trigger a heavy, satisfying sound effect and an immediate screen-flash, instantly transitioning back to the Dashboard to watch the stats explode.

### C. The Council Chamber (The Debate Engine)
This is the heart of the narrative. It triggers when an Adaptation is being debated or a Shrine Upgrade is proposed.

**UI Elements:**
*   **The Round Table**: The 5 Elders (Rowan, Aldric, Tomas, Martha, Elric) are positioned in a semi-circle. 
*   **Elder Tooltips (The "Mind Reading" UI)**: Hovering over an Elder reveals their hidden stats (Mood, Belief, Paranoia). If an Elder is highly paranoid, their avatar should look visibly stressed or shaded in red.
*   **Visual Novel Dialogue**: The debate does not appear all at once. The LLM's dialogue array is streamed message by message.
    *   *Visual Feedback*: If the narrative action says "[Martha slams her fist]", the screen should literally shake. If a character is angry, their text box border should be jagged. 
*   **The Royal Decree**: Once the debate ends, a royal scroll drops down presenting the chosen `Adaptation`. The player must stamp it with a "Divine Seal" to approve it, applying the stat changes.

---

## 3. The "Web of Fate" (Causality UI)

Because the backend uses Cognee Graph RAG to link `parent_situation_id` and `AdaptationMemory`, we can offer the player a truly unique UI view: **The Constellation.**

**UI Elements:**
*   A toggle button switches the screen from the physical kingdom to a starry, abstract constellation map.
*   Nodes represent past Situations (Crises). 
*   Lines connect Crises to the Adaptations built to solve them, which then connect to *new* Crises that those adaptations accidentally caused. 
*   *Dopamine Hit*: This visually proves to the player that their actions have deep, lasting consequences, making the game feel incredibly intelligent.

---

## 4. The Climax: Win / Loss Scenarios

**The Loss (The Mob):**
If Unrest hits 80 and Faith hits 20, the UI immediately locks. The screen tints red. Sirens or war drums play. A final, un-skippable Situation appears: The Mob. The player watches as pixel-art villagers throw torches at the Shrine. The Shrine burns, the UI crumbles into ash, and the game returns to the main menu.

**The Win (The Ascension):**
If Faith is extremely high, the Council debate will propose the *Cathedral of the Heavens*. When the player clicks "Approve", an intense, prolonged particle animation plays. Divine light pierces the clouds, the Shrine physically transforms into a massive monument, and the UI stats shatter, signifying that you are no longer bound by mortal constraints. You have won.
