# 04_development_plan.md

# occasionally_divine — Hackathon Development Plan

**Goal:** Deliver a polished MVP in ~5 days.

---

# Ground Rules

## The Golden Rule

Never build two major systems at once.

Every feature must be:

Build → Run → Test → Commit

before moving forward.

---

# Definition of MVP

A successful demo must show:

1. Player performs disasters.
2. Events are remembered.
3. Council is triggered.
4. Elders discuss history.
5. Kingdom adapts.
6. Same disaster has a different outcome.
7. Chronicle records the event.

Everything else is optional.

---

# Day 1 — Foundation

## Objective

Get a playable shell running.

### Tasks

- Create repository structure.
- Setup FastAPI.
- Setup React + Vite + Tailwind.
- Connect PostgreSQL.
- Create basic world state endpoint.
- Render placeholder UI.

### Deliverable

You can press a button in React and receive a response from FastAPI.

### Verify

- API responds.
- React renders.
- Database connects.

### Commit

`feat: project foundation`

---

# Day 2 — Simulation

## Objective

Build the deterministic game.

### Tasks

- WorldState model
- Resources
- Realm Unrest
- Player actions
- Tile updates
- Event logging

### Deliverable

Flood and Fire visibly change the world.

### Verify

- Resources update correctly.
- Unrest increases.
- Events stored.

### Commit

`feat: simulation loop`

---

# Day 3 — Memory

## Objective

Integrate Cognee.

### Tasks

- remember()
- cognify()
- search()
- Prompt Builder
- Council UI

### Deliverable

Council discussion generated from remembered events.

### Verify

Flood twice.

Council references both floods.

### Commit

`feat: council memory`

---

# Day 4 — Adaptation

## Objective

Complete the magic moment.

### Tasks

- Adaptation application
- Drainage Canals
- Chronicle
- Explain/Memory view

### Deliverable

Flood -> Council -> Canals -> Reduced flood damage.

### Verify

Run complete demo end-to-end.

### Commit

`feat: adaptive kingdom`

---

# Day 5 — Polish

## Tasks

- Better UI
- Loading states
- Icons
- Bug fixes
- Demo script
- README
- Screenshots

Do NOT add new mechanics.

---

# Claude Code Workflow

For every task:

1. Read relevant spec.
2. Implement one subsystem.
3. Run application.
4. Fix errors.
5. Commit.
6. Continue.

Never ask Claude to implement multiple major systems simultaneously.

---

# Recommended Prompt Pattern

```
Read:
03_system_architecture.md

Implement:
Player Action API only.

Requirements:
- No placeholders.
- No TODOs.
- Production-quality code.
- Stop after implementation.
```

---

# Repository Milestones

## Milestone 1

Frontend ↔ Backend communication.

---

## Milestone 2

Simulation works.

---

## Milestone 3

Council works.

---

## Milestone 4

Adaptation works.

---

## Milestone 5

Demo complete.

---

# Daily Definition of Done

Before ending the day:

- App runs.
- No failing startup.
- Feature demonstrated.
- Commit pushed.

---

# Scope Kill List

If behind schedule, remove in this order:

- Fancy animations
- Multiple adaptations
- Extra actions
- Mood variations
- Explain graph visualization

Never remove:

- Council
- Memory
- Adaptation
- Chronicle

---

# Demo Checklist

☐ New game

☐ Flood

☐ Fire

☐ Flood again

☐ Council appears

☐ Dialogue generated

☐ Adaptation built

☐ Flood reduced

☐ Chronicle updated

☐ Explain memory

If all boxes are checked, stop coding.

Ship the demo.
