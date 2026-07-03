# 02_domain_model.md

# occasionally_divine — Domain Model Specification

Version: 1.0
Status: MVP
Audience: Backend, Frontend, AI, Database Engineers

---

# Purpose

This document defines the canonical domain model for Occasionally Divine.

Every subsystem MUST use these entities.

If another specification introduces a conflicting model, this document takes precedence.

---

# Design Principles

- Every entity has a single owner.
- Backend owns simulation.
- Cognee owns memory.
- PostgreSQL owns persistent state.
- React owns presentation.
- LLM never owns state.

---

# Ownership Matrix

| Entity | Backend | PostgreSQL | Cognee | Frontend |
|---------|----------|------------|---------|----------|
| WorldState | ✓ | ✓ | | Read Only |
| Kingdom | ✓ | ✓ | | Read Only |
| Elder | ✓ | ✓ | Personality Context | Display |
| PlayerAction | ✓ | Event Log | Summary | Display |
| HistoricalEvent | ✓ | ✓ | ✓ | Timeline |
| Memory | | | ✓ | Explain View |
| Adaptation | ✓ | ✓ | ✓ | Display |
| ChronicleEntry | ✓ | ✓ | Summary | Display |
| CouncilMeeting | ✓ | ✓ | Context | Display |

---

# Kingdom

Represents the playable civilization.

Fields

- id
- name
- current_year
- current_season
- food
- faith
- population
- realm_unrest
- divine_influence

Relationships

Kingdom
├── Elders
├── Adaptations
├── Chronicle
└── WorldState

Lifecycle

Created once at new game.

Never replaced.

---

# WorldState

Snapshot of current simulation.

Contains

- map tiles
- buildings
- resources
- disasters
- active adaptations

The frontend renders only this object.

---

# Elder

Persistent council member.

Fields

- id
- name
- role
- mood
- personality_key

Mood changes.

Personality never changes.

Personality definitions come from
01c_elder_bible.md

---

# PlayerAction

Represents one divine intervention.

Fields

- action_type
- timestamp
- season
- cost
- effects

Every PlayerAction creates one HistoricalEvent.

---

# HistoricalEvent

Objective record.

Examples

Flood

Fire

Bless Harvest

Contains

- event id
- type
- season
- year
- location
- effects

Stored in PostgreSQL.

Summarized into Cognee.

---

# Memory

Semantic representation of history.

Owned exclusively by Cognee.

Example

"Repeated flooding damaged eastern farmland."

Never mutate directly.

Created through remember() and cognify().

---

# CouncilMeeting

Represents one completed council.

Fields

- id
- trigger
- retrieved_memories
- discussion
- proposal
- adaptation
- chronicle_entry

Exactly one adaptation per meeting.

---

# Adaptation

Permanent civilization improvement.

Fields

- id
- display_name
- trigger_events
- gameplay_effect
- constructed_year

Examples

Drainage Canals

Stone Houses

Granaries

Adaptations never expire in MVP.

---

# ChronicleEntry

Player-facing history.

Fields

- season
- year
- summary
- consequence

Generated after every council.

Chronicle entries are immutable.

---

# Relationships

PlayerAction
    ↓
HistoricalEvent
    ↓
Memory (Cognee)
    ↓
CouncilMeeting
    ↓
Adaptation
    ↓
ChronicleEntry
    ↓
WorldState

---

# Serialization Rules

Backend DTOs MUST use snake_case.

Frontend Types MAY convert to camelCase.

Dates represented as

year + season

No real timestamps required.

---

# Validation Rules

Kingdom

- faith >= 0
- population >= 0
- unrest 0..100

Adaptation

- unique id
- cannot already exist

CouncilMeeting

- exactly one proposal
- exactly one chronicle entry

---

# AI Agent Notes

Never store duplicate concepts.

Do not let Cognee become the source of truth for resources.

Resources live in PostgreSQL.

Cognee stores meaning.

PostgreSQL stores facts.

This separation is mandatory.

---

# MVP Checklist

- Kingdom
- WorldState
- Elder
- PlayerAction
- HistoricalEvent
- Memory
- CouncilMeeting
- Adaptation
- ChronicleEntry
