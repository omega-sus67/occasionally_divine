# occasionally_divine

## Project Vision Document (PVD)

---

> **Version:** 2.0
>
> **Status:** Design Phase
>
> **Project Type:** AI-Driven Strategy Simulation
>
> **Development Window:** 5-Day Hackathon MVP
>
> **Primary Objective:** Demonstrate persistent AI memory through emergent gameplay.

---

# Table of Contents

1. Introduction
2. Vision
3. Product Philosophy
4. Project Goals
5. Core Gameplay Philosophy
6. Design Principles
7. Player Fantasy
8. Medieval World Philosophy
9. AI Philosophy
10. MVP Philosophy
11. Success Criteria
12. Development Constraints

---

# 1. Introduction

Occasionally Divine is an AI-driven medieval strategy simulation where the player influences the evolution of a small kingdom through indirect divine intervention.

Unlike traditional strategy games, the player's primary opponent is not the kingdom itself.

The opponent is the kingdom's ability to learn.

Every flood...

Every fire...

Every miracle...

Every blessing...

becomes part of the civilization's permanent memory.

The kingdom slowly transforms accumulated experience into collective wisdom.

The player must continually invent new strategies before the kingdom learns how to resist them.

The project is therefore not a simulation of destruction.

It is a simulation of **adaptation**.

---

# 2. Vision

Most AI demonstrations answer questions.

Some play games.

Some generate images.

Very few demonstrate long-term memory in a way that humans immediately understand.

Knowledge Graphs are powerful.

Unfortunately, they are invisible.

Most people cannot appreciate a graph database by looking at nodes and relationships.

Occasionally Divine exists to solve this problem.

Instead of visualizing a graph...

we visualize its consequences.

The player never sees

```
Village
    |
experienced
    |
Flood
```

Instead they see

> The kingdom builds drainage canals because it remembers previous floods.

Memory becomes visible.

History becomes gameplay.

---

# Vision Statement

> **Create a living medieval civilization whose decisions become progressively more intelligent because its memories never disappear.**

---

# 3. Product Philosophy

This project is not attempting to build a complete strategy game.

It is not attempting to rival games such as RimWorld, Civilization or Banished.

Those games simulate economies.

Occasionally Divine simulates memory.

Every mechanic should strengthen one central idea.

> **History changes the future.**

If a mechanic does not reinforce this idea...

it does not belong in Version 1.

---

# Product Identity

Occasionally Divine is best described as

> **An AI-driven strategy simulation demonstrating persistent collective memory using Knowledge Graphs.**

It should never be described as

* a city builder
* an RTS
* a survival game
* an RPG

Those genres create incorrect expectations.

---

# 4. Project Goals

The project has four goals.

---

## Goal 1

Demonstrate persistent memory.

The kingdom should visibly remember previous events.

---

## Goal 2

Demonstrate adaptation.

Past experiences should alter future decisions.

---

## Goal 3

Demonstrate explainability.

The player should always be able to answer

> "Why did this happen?"

The game should never require

> "Because the AI decided."

---

## Goal 4

Produce a polished hackathon demonstration that highlights

* React
* FastAPI
* Cognee
* PostgreSQL
* LLM reasoning
* Event-driven architecture

rather than graphical complexity.

---

# 5. Core Gameplay Philosophy

The player does not directly control the kingdom.

Instead, the player influences history.

History influences memory.

Memory influences discussion.

Discussion influences adaptation.

Adaptation influences future history.

Everything in the game follows this recursive cycle.

```
Player

↓

History

↓

Memory

↓

Discussion

↓

Adaptation

↓

History
```

History is therefore the true protagonist of the game.

---

# 6. The Five Design Pillars

Every mechanic introduced into Occasionally Divine must satisfy at least one of these principles.

## Pillar One

### History Matters

Important events permanently influence future gameplay.

Nothing significant should be forgotten.

---

## Pillar Two

### Knowledge Evolves

The kingdom should continuously become more capable.

The player should feel increasing resistance as the game progresses.

---

## Pillar Three

### Personality Persists

Each elder should feel like a recognizable character.

Their mood changes.

Their personality does not.

The Merchant should still sound like the Merchant.

The Priest should still sound like the Priest.

Even after twenty council meetings.

---

## Pillar Four

### Explainability First

Every adaptation must be explainable through previous events.

The Knowledge Graph should always provide the reasoning chain.

---

## Pillar Five

### Stories Emerge Naturally

Players should remember stories.

Not mechanics.

Example

> "I poisoned the wells after they built canals."

is more valuable than

> "I unlocked Disaster Tier II."

---

# 7. Player Fantasy

The player is deliberately undefined.

The game never explicitly states

* god
* demon
* spirit
* deity

The villagers merely observe that strange events occasionally occur.

Some interpret these events as divine intervention.

Others see coincidence.

Others believe curses.

The ambiguity is intentional.

It allows the kingdom to construct its own mythology over time.

The player becomes a force of history rather than a visible character.

---

# 8. Medieval World Philosophy

The medieval setting was chosen because it naturally supports:

* folklore
* superstition
* religion
* famine
* plague
* engineering
* harvest cycles
* oral tradition

The world should feel grounded rather than fantastical.

Magic belongs to the player.

The kingdom itself remains believable.

Villagers solve problems with

* tools
* labor
* cooperation
* faith

—not magic.

This contrast strengthens the player's supernatural identity.

---

# 9. AI Philosophy

Artificial Intelligence exists to improve immersion.

It should never replace deterministic systems.

Responsibilities are strictly separated.

## LLM

Responsible for

* dialogue
* reasoning
* historical summaries
* explanations

The LLM never decides

* game rules
* probabilities
* resource changes
* victory conditions

---

## Backend

Responsible for

* simulation
* resources
* turn progression
* adaptation success
* deterministic logic

---

## Cognee

Responsible for

* persistent memory
* historical relationships
* retrieval
* contextual knowledge

---

## PostgreSQL

Responsible for

* authoritative world state
* saves
* resources
* entity persistence

---

# 10. MVP Philosophy

This project must be completed in approximately five days.

Therefore simplicity is a design requirement.

The MVP intentionally contains

* one kingdom
* one map
* one council
* five elders
* six divine actions
* one Knowledge Graph
* one Royal Chronicle

Everything else belongs to future versions.

The project is successful when

players understand

> "The kingdom learned."

It is **not** successful because

* graphics look impressive
* animations are complex
* many mechanics exist

Visible intelligence is always prioritized over visual fidelity.

---

# 11. Success Criteria

The demo should require approximately two minutes.

An observer should witness

1. A divine action.
2. Rising Realm Unrest.
3. The Council of Elders assembling.
4. Retrieval from the Knowledge Graph.
5. Dialogue generated from historical context.
6. A new adaptation.
7. The same disaster producing a different outcome because the kingdom remembered.

If that sequence succeeds...

the project succeeds.

---

# 12. Development Constraints

The following constraints are mandatory.

## Scope Constraints

Exactly one kingdom.

Exactly one screen.

Exactly one council.

Maximum five elders.

Maximum six player actions.

No real-time gameplay.

No physics.

No procedural terrain.

No pathfinding.

No inventory.

No combat.

No multiplayer.

No generated art.

No voice acting.

Every excluded feature is excluded intentionally.

---

## Engineering Constraint

Whenever implementation complexity conflicts with gameplay value,

**choose the simpler implementation.**

A working demonstration of persistent memory is more valuable than an unfinished simulation.

---

# Final Principle

Every feature should answer one question.

> **Does this make the kingdom feel like it remembers?**

If the answer is "no,"

the feature should either be simplified,

moved to Future Scope,

or removed entirely.

Occasionally Divine is not a game about destruction.

It is a game about memory becoming civilization.
