# Occasionally Divine — Data Model Design Guide

> This document explains every class and parameter in [`domain.py`](file:///home/omega_sus/Desktop/cognee_/occasionally_divine/backend/models/domain.py), why they exist, what values they take, and how they feed into the LLM Situation Engine, the Cognee Knowledge Graph, and the Council debate system.

---

## How to Read This Document

Each model is documented with:
- **Purpose**: What this table represents in the game world.
- **Parameters**: Every column, its type, its range of valid values, and its narrative importance.
- **Feeds Into**: Which systems (LLM, Cognee, Council, Frontend) consume this data.
- **Design Rationale**: Why this exists — what story it enables.

---

## 1. Kingdom

**Purpose**: The single source of truth for the entire game state. There is exactly ONE Kingdom per game. Every other table references it. If you understand this table, you understand the game.

**Table**: `kingdoms`

| Parameter | Type | Default | Range | Purpose |
|---|---|---|---|---|
| `id` | Integer (PK) | Auto | — | Unique identifier |
| `name` | String | `"Valoria"` | Any string | The kingdom's name. Seeded as `"Edengrove"`. Used in all LLM prompts so the AI refers to the kingdom by name. |
| `current_year` | Integer | `1` | 1 → ∞ | The current in-game year. Increments when seasons cycle back to Spring. Used to timestamp every event, chronicle entry, and adaptation. |
| `current_season` | String | `"Spring"` | `Spring`, `Summer`, `Autumn`, `Winter` | Cycles through the four seasons. Each situation resolves one season. Affects which situations the LLM generates (droughts in summer, blizzards in winter). |
| `food` | Integer | `50` | 0–100 | **Core Resource.** Represents the kingdom's food reserves. When food hits 0, the kingdom starves and population drops. When food is high, the people are content. The LLM sees this and generates harvest situations when food is low, or trade opportunities when it's high. |
| `faith` | Integer | `100` | 0–100 | **Core Resource.** How much the people believe in the divine (the player). When faith drops to 0, the people stop listening to divine interventions entirely. Aldric (the priest) will panic in council debates when faith is low. |
| `population` | Integer | `1000` | 0 → ∞ | The number of villagers. Currently not actively modified by most actions, but serves as a game-over condition and a scaling factor for future systems (e.g., "a famine killed 200 people"). |
| `realm_unrest` | Integer | `20` | 0–100 | **The Council Trigger.** When this hits 100, the Council of Elders automatically convenes. Every disaster increases it, every blessing decreases it. This is the central tension meter of the entire game. |
| `divine_influence` | Integer | `50` | 0–`divine_influence_max` | **The Player's Budget.** Every intervention costs divine influence. This prevents the player from spamming blessings. It regenerates slowly between seasons. Think of it as "mana" for a god. |
| `divine_influence_max` | Integer | `100` | 50–200 | The cap on divine influence. Can be increased through certain adaptations or high faith. |
| `initial_morale` | Integer | Random (0-100) | 0–100 | **Randomized per game.** Set once at kingdom creation and never changed. Represents the kingdom's "baseline personality." A kingdom born with morale 80 (near despair) starts grim — the LLM generates bleaker narratives from the start. The delta between `initial_morale` and `current_morale` tells the LLM whether things are getting better or worse. |
| `current_morale` | Integer | Same as initial | 0–100 | **0 = Hope, 100 = Despair.** Modified by interventions, disasters, and council decisions. Fed directly into the LLM prompt. A kingdom at morale 90 generates situations about riots, mass prayer, and exodus. A kingdom at morale 10 generates festivals, trade deals, and expansion plans. |
| `trust_in_ruling_class` | Integer | `50` | 0–100 | **Political Tension Axis.** Creates story forks that food/faith alone cannot: Low trust + high unrest = revolution. High trust + high faith = theocratic obedience. High trust + low food = the people starve quietly, trusting that "the elders know best." This gives the LLM a political dimension to write about. |
| `weather` | String | `"Clear"` | `Clear`, `Rain`, `Storm`, `Drought`, `Fog` | **Atmosphere Engine.** Affects which situations are plausible. The LLM won't generate a drought situation during a Storm. Also sets the visual tone for the frontend map (rain particles, fog overlay, etc.). |
| `omen_active` | String | `None` | `None`, `"Blood Moon"`, `"Comet"`, `"Eclipse"` | **Narrative Spice.** An active omen amplifies the LLM's tone. A council meeting under a Blood Moon generates panicked, superstitious dialogue. Omens are temporary and cleared after a few seasons. |
| `consecutive_disasters` | Integer | `0` | 0 → ∞ | **Theme Escalation.** Tracks how many disasters have occurred in a row without a blessing or calm period. At 3+, the LLM starts generating themed situations ("The River Claims Another Season"). At 5+, the kingdom develops a cultural identity around suffering. Fed to Cognee to build memory themes. |

**Relationships**: Links to every other table. The Kingdom is the root node of the entire data graph.

**Feeds Into**: Everything. The Situation Engine reads Kingdom stats to generate contextual events. The Council Engine reads it for debate context. Cognee stores Kingdom state snapshots as memories. The frontend reads it for resource bars and status display.

---

## 2. WorldState

**Purpose**: The physical map of the kingdom — a 5×5 tile grid with buildings, disasters, and the emotional distribution of the population. One WorldState per Kingdom.

**Table**: `world_states`

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `kingdom_id` | FK → Kingdom | — | Links this map to its kingdom |
| `population_mood_json` | Text (JSON) | `{"hopeful": 40, "fearful": 20, "angry": 10, "devoted": 30}` | **Mood Distribution.** Instead of one number for "mood," this is a distribution. A kingdom can be 50% fearful and 30% devoted simultaneously — that's a population praying out of terror. Fed to the LLM for nuanced narrative: *"The chapel overflows each night, though none pray with joy."* |
| `tiles_json` | Text (JSON) | `[]` | Array of 25 tile objects (5×5 grid). Each tile has `id`, `type` (`River`/`Farmland`/`Forest`/`Village`), `status` (`Normal`/`Flooded`/`Burned`), and `x`/`y` coordinates. The frontend renders this as the visual map. |
| `buildings_json` | Text (JSON) | `[]` | Array of building objects on tiles. Each has `id`, `name` ("Chapel", "Tomas' Forge"), `type` (`Church`/`Blacksmith`/`Tavern`/`House`), `status`, and `tile_id`. Buildings can be destroyed by fire and rebuilt by adaptations. |
| `disasters_json` | Text (JSON) | `[]` | Array of active disaster effects on the map. Used for visual rendering and situation generation. |

**Mood Distribution Values**:

| Mood | What it means | When it rises |
|---|---|---|
| `hopeful` | People believe tomorrow will be better | After blessings, good harvests, calm seasons |
| `fearful` | People expect the worst | After disasters, omens, consecutive calamities |
| `angry` | People blame the rulers | When food is low AND trust_in_ruling_class is low |
| `devoted` | People turn to religion | When faith is high AND fearful is also high (praying out of fear) |

**Design Rationale**: The mood distribution is the secret weapon for LLM narrative diversity. A kingdom that is `{"hopeful": 10, "fearful": 60, "angry": 5, "devoted": 25}` generates completely different situations than one at `{"hopeful": 50, "fearful": 5, "angry": 30, "devoted": 15}`, even if their food/faith/unrest numbers are identical.

---

## 3. Elder

**Purpose**: The five members of the Council. Each elder is a unique personality that the LLM voices during debates. Their stats evolve over the course of the game based on what happens.

**Table**: `elders`

| Parameter | Type | Default | Range | Purpose |
|---|---|---|---|---|
| `name` | String | — | `Rowan`, `Aldric`, `Tomas`, `Martha`, `Elric` | The elder's name. Fixed across all games. |
| `role` | String | — | `"Elder Rowan"`, `"Brother Aldric"`, etc. | Their title. Used in UI display and LLM prompt context. |
| `mood` | String | `"Neutral"` | `Neutral`, `Angry`, `Fearful`, `Hopeful`, `Grieving` | Current emotional state. Changes after council meetings and major events. Fed to LLM: an angry Tomas speaks differently than a grieving Tomas. |
| `personality_key` | String | — | e.g., `"leader_pragmatic"`, `"priest_doomsayer"`, `"builder_paranoid"` | **Randomly selected from `elder_personalities.json` at game start.** This is the core identity. A `priest_corrupt` Aldric plays completely differently from a `priest_compassionate` one. There are 3 variants per elder = **243 possible council combinations.** |
| `stance` | String | nullable | `"pro-faith"`, `"pro-engineering"`, `"pro-survival"`, `"pro-wealth"`, `"pro-nature"`, etc. | Their current political position. Affects which adaptations they argue for in council. Can shift over time (e.g., a pragmatic Rowan might become pro-faith after witnessing 3 divine blessings). |
| `memorable_quote` | Text | nullable | Any string | **The LLM's memory of itself.** After each council, the most impactful line an elder said gets saved here. In the next council, this quote is fed back to the LLM: *"Last time, Tomas said: 'Stone listens better than prayer.' Build on this personality."* This creates the illusion of persistent character. |
| `times_agreed` | Integer | `0` | 0 → ∞ | How many times this elder's proposal was accepted by the council. An elder who always wins becomes confident. The LLM can write them as smug or assured. |
| `times_dissented` | Integer | `0` | 0 → ∞ | How many times this elder opposed the majority. An elder who constantly disagrees becomes either a prophet ("I warned you!") or a pariah ("Nobody listens to the merchant."). |
| `belief_in_divine` | Integer | Varies | 0–100 | **How much this elder believes the player (god) exists.** Aldric might start at 100 (absolute believer). Tomas might start at 10 (rationalist). After witnessing multiple divine interventions, even a skeptic's number rises. This affects council dialogue: a non-believer attributes blessings to luck, a believer attributes disasters to divine punishment. |

**The 5 Elders and Their Roles**:

| Elder | Role | What They Care About | Typical Stance |
|---|---|---|---|
| **Rowan** | Village Leader | Balance, tradition, stability | Moderate — tries to unify the council |
| **Aldric** | Priest | Faith, divine will, moral purity | Pro-faith — interprets everything through religion |
| **Tomas** | Master Builder | Infrastructure, engineering, defense | Pro-engineering — wants walls, canals, fortifications |
| **Martha** | Farmer | Food, land, practical survival | Pro-agriculture — focuses on crops and granaries |
| **Elric** | Merchant | Trade, wealth, opportunity | Pro-economy — sees profit in every crisis |

**Design Rationale**: The elder system is what makes the Council *the reward* rather than an interruption. When the LLM is given a frustrated Tomas (`times_dissented=4`, `mood="Angry"`, `memorable_quote="I told you the walls would fall"`), it generates a character arc naturally — without any scripted dialogue trees.

---

## 4. PlayerAction

**Purpose**: A timestamped log of every action the player has taken. This is the player's "divine footprint" in history.

**Table**: `player_actions`

| Parameter | Type | Purpose |
|---|---|---|
| `action_type` | String | What the player did. Now always `"Intervention"` since the Situation Engine replaced static actions. |
| `cost` | Integer | How much divine influence was spent. |
| `season` / `year` | String / Integer | When it happened. Used to build timelines. |
| `timestamp` | String (ISO) | Server timestamp for debugging and replay. |

**Feeds Into**: Cognee stores the pattern of player actions to detect divine "personality" — is this a wrathful god (lots of disasters) or a nurturing one (lots of blessings)?

---

## 5. HistoricalEvent

**Purpose**: The kingdom's factual historical record. Every resolved situation, every council decision, every disaster creates one. This is the raw data that Cognee turns into a knowledge graph.

**Table**: `historical_events`

| Parameter | Type | Default | Range | Purpose |
|---|---|---|---|---|
| `type` | String | — | `"Situation Resolved"`, `"Council Decision"`, etc. | What kind of event this was. |
| `description` | Text | — | — | A narrative summary: *"In response to 'The River Grows Restless', the divine action was taken: 'Bless the fields with sudden rain'."* This exact string is sent to Cognee for ingestion into the knowledge graph. |
| `severity` | Integer | `1` | 1–5 | **How impactful this event was.** Severity 1 = minor footnote. Severity 5 = kingdom-defining moment. When Cognee retrieves memories, high-severity events are prioritized. A severity-5 flood will be remembered for decades; a severity-1 drizzle will be forgotten. |
| `category` | String | — | `Nature`, `Society`, `Economy`, `Religion`, `Infrastructure`, `Mystery` | **Groups events into themes.** Cognee can query: "Retrieve all Nature events" to give the council context about environmental history. |
| `theme` | String | nullable | `"The River"`, `"The Flame"`, `"The Harvest"`, `"The Plague"`, etc. | **Cultural memory tags.** When the same theme appears 3+ times, the kingdom develops a *cultural identity* around it. A kingdom with 5 "River" events becomes known as "the people who fear the water." The LLM uses this to generate themed situations and the Royal Chronicle writes about "the old river curse." |
| `times_referenced` | Integer | `0` | 0 → ∞ | **How often this event has been mentioned.** Every time a council or situation references a past event, this counter increments. Events with high reference counts become myths. The LLM can say: *"the flood that everyone still speaks of."* |
| `effects_json` | Text (JSON) | `{}` | `{"food": -10, "faith": 5, ...}` | The mechanical effects that were applied. Stored for Cognee to build causal graphs: `Flood → caused → food -15`. |

**Design Rationale**: This is the bridge between the deterministic backend and the narrative LLM. The backend writes cold facts here. Cognee reads them and builds a semantic web. The LLM then references that web to generate situations that are historically aware.

---

## 6. Adaptation

**Purpose**: Permanent improvements the Council votes to build. These are the kingdom "learning" from its mistakes — the core game progression mechanic.

**Table**: `adaptations`

| Parameter | Type | Default | Range | Purpose |
|---|---|---|---|---|
| `display_name` | String | — | `"Drainage Canals"`, `"Stone Houses"`, `"Granaries"`, etc. | The name of the adaptation. Shown in UI and used by the LLM in council debates. |
| `gameplay_effect` | String | — | — | A description of the mechanical effect: *"Reduces flood food loss from 15 to 5"*. |
| `status` | String | `"proposed"` | `proposed` → `constructing` → `halted` → `disputed` → `completed` | **The lifecycle.** Adaptations don't appear instantly. They are proposed by the council, then take time to build. They can be halted by disasters (flood destroys half-built canals) or disputed by elders (Elric argues it's too expensive). This creates multi-season story arcs around a single construction project. |
| `construction_started_season` / `_year` | String / Integer | nullable | — | When construction began. Used to calculate completion. |
| `speed` | Integer | `1` | 1–4 | **How many years to complete.** A speed-1 adaptation finishes in one year. A speed-4 mega-project takes four years — during which anything can go wrong. The council might halt it, a disaster might destroy progress, or the elders might vote to redirect resources. |
| `trigger_events_json` | Text (JSON) | `[]` | — | Which historical events caused this adaptation to be proposed. Stored for Cognee: `Flood Year 2 → triggered → Drainage Canals proposal`. |

**Current Adaptations**:

| Adaptation | Effect | Mitigates |
|---|---|---|
| Drainage Canals | Reduces flood food loss from 15 to 5 | Flood disasters |
| Stone Houses | Prevents building destruction by fire | Fire disasters |
| Granaries | Increases blessing food gain from 15 to 25 | Famine situations |

**Design Rationale**: Adaptations are the visible proof that "the kingdom learns." A kingdom in Year 20 with Drainage Canals, Stone Houses, and Granaries is fundamentally more resilient than Year 1. But each adaptation was hard-won through a council debate — it carries the weight of history.

---

## 7. ChronicleEntry

**Purpose**: The Royal Chronicle — the player's reward. Each entry is a page in the kingdom's history book, written by an invisible historian in medieval prose.

**Table**: `chronicle_entries`

| Parameter | Type | Purpose |
|---|---|---|
| `title` | String | A poetic title: *"The Great Flood"*, *"The Year of Empty Granaries"*, *"When the Builder Wept"*. Generated by the LLM. |
| `narrative` | Text | 3–6 paragraphs of LLM-generated medieval prose. This is the actual "page" the player reads. Should feel like a passage from a history book, not a game log. |
| `summary` | Text | A shorter factual summary for UI tooltips and Cognee ingestion. |
| `consequence` | Text | What changed as a result: *"The council authorized construction of Drainage Canals."* |
| `legacy` | Text (nullable) | A one-line sentence that echoes forward in time: *"From that year onward, the kingdom feared the river less."* Future council meetings can quote this line. |
| `historian_tone` | String | Tracks the current emotional register of the chronicle: `hopeful`, `fearful`, `resigned`, `defiant`, `mournful`. The LLM uses this to maintain consistent tone across entries. A kingdom that has been suffering for 10 years shouldn't suddenly have a cheerful historian voice. |

**Design Rationale**: The Chronicle is *the point of the game*. The Bible of Design says: "the player's reward is stories, not scores." Every chronicle entry should make the player feel like they are reading the history of a real civilization. The `historian_tone` ensures that the writing evolves — a hopeful kingdom's chronicle reads like early Rome; a suffering one reads like the fall of Constantinople.

---

## 8. CouncilMeeting

**Purpose**: A record of every time the Council of Elders convened. Stores the debate, the emotions, and the final decision.

**Table**: `council_meetings`

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `trigger` | String | — | What caused the council to meet: `"Unrest threshold reached"`, `"Emergency flood"`, etc. |
| `retrieved_memories_json` | Text (JSON) | `[]` | The memories Cognee returned when asked about the current crisis. These are the "past events" that the elders reference in debate. Stored so we can audit what the council "knew" when it made its decision. |
| `discussion_json` | Text (JSON) | `[]` | Array of `{"speaker": "Rowan", "dialogue": "..."}` objects. The full debate transcript. Generated by the LLM using elder personalities, stances, and beliefs. |
| `proposal` | String | — | The adaptation the council decided on: `"Drainage Canals"`, `"Stone Houses"`, etc. |
| `adaptation_id` | FK → Adaptation | nullable | Links to the adaptation that was created from this decision. |
| `dominant_emotion` | String | nullable | `"anger"`, `"grief"`, `"hope"`, `"fear"`, `"determination"` | The overall emotional register of the meeting. A council with `dominant_emotion="grief"` and `dissent_level=10` is a solemn, united meeting. One with `"anger"` and `dissent_level=90` is a screaming match. |
| `dissent_level` | Integer | `0` | 0–100 | How much the elders disagreed. Low dissent = consensus. High dissent = fractured council. At dissent > 80, the adaptation might be `"disputed"` instead of `"constructing"`. |

**Design Rationale**: The council is "the reward, not the interruption." By storing rich emotional data alongside the decision, we allow the Chronicle to write dramatically different entries. A unanimous council that built canals in grief is a completely different story than a fractured council that barely agreed to build them through screaming.

---

## 9. Situation

**Purpose**: The heart of the game. Each situation is a unique, LLM-generated event that the player must respond to. Replaces the old static action menu.

**Table**: `situations`

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `title` | String | — | A narrative title: *"The River Grows Restless"*, *"A Merchant Arrives at Dawn"*, *"The Children Won't Stop Singing"*. |
| `narrative` | Text | — | 2–3 paragraphs describing the problem. Written in medieval, slightly poetic tone. This is what the player reads before making their choice. |
| `category` | String | — | `Nature`, `Society`, `Economy`, `Religion`, `Infrastructure`, `Mystery`. Determines which elders care most about this event and affects theme tracking. |
| `severity` | Integer | `1` | 1–5 | How urgent the situation is. Severity 5 situations have extreme effects and demand immediate response. Severity 1 situations are ambient flavor. |
| `interventions_json` | Text (JSON) | — | Array of 4 intervention objects, each with `description` (what the player does), `cost` (divine influence), and `effects` (JSON of stat changes). One intervention is always "Do nothing" with cost 0. |
| `chosen_intervention` | String | nullable | Which intervention the player selected. Set after the player acts. `null` means the situation is still pending. |
| `parent_situation_id` | FK → Situation | nullable | **Causal chaining.** If this situation was caused by a previous one, this links back to it. Creates chains: `Heavy Rain → River Overflowing → Families Evacuate → Council Convenes`. Cognee can traverse these chains to understand cause and effect. |

**Intervention Structure**:
```json
{
    "description": "Bless the fields with sudden rain",
    "cost": 25,
    "effects": {
        "food": 15,
        "faith": 10,
        "unrest": -5,
        "morale": -10
    }
}
```

**Design Rationale**: The Situation is what makes every game unique. Because the LLM generates them based on the current world state, two kingdoms with the same food/faith/unrest might get completely different situations based on their weather, morale, or active omen. The `parent_situation_id` chaining means consequences cascade — a flood in Year 1 can echo through 10 connected situations across 5 years.

---

## 10. Rumor

**Purpose**: The chaos engine. Rumors introduce false or unverified information into the kingdom's collective memory. They can influence council decisions, create panic, or turn out to be prophetic.

**Table**: `rumors`

| Parameter | Type | Default | Range | Purpose |
|---|---|---|---|---|
| `content` | Text | — | — | The rumor itself: *"Merchants say the western kingdom fell to plague"*, *"The river spirit demands a sacrifice"*. |
| `source_elder` | String | nullable | Any elder name | Who started the rumor (if known). A rumor from Elric ("I heard from traders...") is different from one from Aldric ("The scriptures warn..."). |
| `is_true` | Integer | `-1` | `-1` (unknown), `0` (false), `1` (true) | **Truth is uncertain.** When a rumor is created, nobody knows if it's true. As the game progresses, events might confirm or deny it. A "plague from the west" rumor that starts false could become true if the kingdom's food drops to 0. |
| `spread` | Integer | `0` | 0–100 | How many villagers believe the rumor. At spread > 60, it functionally becomes "truth" in the kingdom's culture — even if `is_true = 0`. The council will debate it as though it's real. |

**Design Rationale**: Rumors are the most historically accurate mechanic in the game. Real civilizations made decisions based on false information constantly. A kingdom might build a wall against a plague that never comes — and that wall might save them from a real flood years later. Cognee stores rumors as memories indiscriminately, which means the LLM might reference a false rumor as though it were history. This is intentional — it simulates oral tradition.

---

## System Integration Map

```
┌──────────────────────────────────────────────────────────────┐
│                     PLAYER (The God)                         │
│                 Sees: Situations, Chronicle, Map             │
│                 Acts: Chooses an Intervention                │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              SITUATION ENGINE (LLM-generated)                │
│  Reads: Kingdom stats, weather, morale, Cognee memories      │
│  Writes: Situation → interventions_json                      │
│  Output: 4 contextual choices for the player                 │
└──────────────────────┬───────────────────────────────────────┘
                       │ Player chooses intervention
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              ACTION HANDLER (Deterministic)                   │
│  Reads: intervention.effects JSON                            │
│  Writes: Kingdom (food, faith, unrest, morale)               │
│  Writes: HistoricalEvent, PlayerAction                       │
│  Writes: Cognee memory (description string)                  │
└──────────────────────┬───────────────────────────────────────┘
                       │ If realm_unrest >= 100
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              COUNCIL ENGINE (LLM-generated debate)           │
│  Reads: Elder personalities, stances, beliefs                │
│  Reads: Cognee retrieved memories                            │
│  Writes: CouncilMeeting, Adaptation, ChronicleEntry          │
│  Output: A debate transcript + proposed adaptation           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              COGNEE KNOWLEDGE GRAPH                           │
│  Stores: HistoricalEvent descriptions, Rumor content         │
│  Retrieves: Relevant memories for Situations & Council       │
│  Builds: Entity relationships (Flood → damaged → Farmlands)  │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

1. **The backend owns facts.** Every stat change goes through the deterministic Action Handler. The LLM never directly modifies the database.
2. **The LLM owns language.** It generates narratives, debates, and chronicle entries. It proposes effects as JSON, but the backend validates and applies them.
3. **Cognee owns memory.** It stores historical events as a semantic graph and retrieves relevant memories when the Situation Engine or Council Engine needs context.
4. **Every parameter tells a story.** There are no "just-a-number" fields. Every integer, every string, feeds into an LLM prompt that generates narrative. `trust_in_ruling_class = 12` isn't a stat — it's the difference between a council meeting and a revolution.
