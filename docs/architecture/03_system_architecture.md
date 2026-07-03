# 03_system_architecture.md

# occasionally_divine — MVP System Architecture

Version: 1.0
Audience: Claude Code, Backend, Frontend

---

# Goal

Build ONE unforgettable demo.

The architecture exists to demonstrate:

Player Action
→ Persistent Memory
→ Council Discussion
→ Adaptation
→ Different Future

Nothing else.

---

# Tech Stack

Frontend
- React
- Vite
- TailwindCSS
- React Query

Backend
- FastAPI
- SQLAlchemy
- PostgreSQL

AI
- Cognee
- Ollama (Qwen 2.5 3B or API-compatible model)

---

# High Level Architecture

```
                React Frontend
                      │
               REST API (FastAPI)
                      │
      ┌───────────────┼──────────────┐
      │               │              │
Simulation      PostgreSQL      Cognee
      │               │              │
      └───────────────┼──────────────┘
                      │
              Prompt Builder
                      │
                     LLM
                      │
               Council Response
```

---

# Responsibilities

## React

Responsible for:

- Tile map
- Resources
- Council UI
- Chronicle
- Action buttons

React never contains game logic.

---

## FastAPI

Responsible for:

- Rules
- Resources
- Turn progression
- Council trigger
- Adaptations

FastAPI is the source of truth.

---

## PostgreSQL

Stores

- Kingdom
- Resources
- Adaptations
- Chronicle
- Events

Never stores prompts.

---

## Cognee

Stores

- Memories
- Relationships
- Disaster history

Used only during council.

---

## LLM

Responsible only for:

- Council dialogue
- Proposal wording
- Chronicle prose

Never calculates gameplay.

---

# Folder Structure

```
occasionally_divine/

backend/
    api/
    services/
    models/
    prompts/
    council/
    simulation/

frontend/
    components/
    pages/
    hooks/
    api/

spec/

assets/
```

---

# Request Lifecycle

## Player clicks Flood

Frontend

↓

POST /player_action

↓

Backend validates

↓

Simulation updates

↓

Event written

↓

cognee.remember()

↓

Response

↓

Frontend updates map

No LLM call.

---

# Council Lifecycle

Realm Unrest >= 100

↓

Pause gameplay

↓

cognee.cognify()

↓

Retrieve memories

↓

Build prompt

↓

LLM

↓

Validate proposal

↓

Apply adaptation

↓

Chronicle entry

↓

Resume gameplay

---

# API Endpoints

POST /player_action

GET /world_state

POST /trigger_council

GET /chronicle

GET /memory

---

# Build Order

## Phase 1

- FastAPI
- React
- PostgreSQL

Goal:
Clickable UI.

---

## Phase 2

- Tilemap
- Resources
- Player actions

Goal:
Playable loop.

---

## Phase 3

- Cognee
- Council
- Prompt

Goal:
Memory works.

---

## Phase 4

- Adaptations
- Chronicle
- Explain View

Goal:
Demo complete.

---

# Performance Rules

- Never call the LLM after every action.
- Council is the only expensive operation.
- Keep prompts under ~1200 tokens.
- One council at a time.

---

# What NOT To Build

- Multiplayer
- Pathfinding
- Individual villagers
- Dynamic economy
- Politics
- Cultists
- Procedural maps
- Voice
- Inventory

If unsure whether to implement a feature:

Don't.

---

# Demo Script (2–3 minutes)

1. Start new kingdom.
2. Flood.
3. Fire.
4. Flood again.
5. Realm Unrest reaches 100.
6. Council discusses history.
7. Canals built.
8. Flood again.
9. Reduced damage.
10. Open Kingdom Memory to show why.

If this works, the MVP is successful.

---

# AI Agent Notes

Implement in this order:

1. Backend simulation
2. Database
3. REST API
4. React UI
5. Cognee integration
6. Prompt builder
7. Council
8. Chronicle

Never implement future features before the demo loop works.

---

# Definition of Done

A judge can understand the entire project in under three minutes without explanation.

The kingdom visibly remembers.

The player notices the adaptation.

The Chronicle records it.

Mission accomplished.
