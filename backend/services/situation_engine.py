import json
import random
import asyncio
from sqlalchemy.orm import Session
from models.domain import Kingdom, Situation, Elder, ChronicleEntry, CouncilMeeting, Rumor, HistoricalEvent
from models.cognee_schemas import RumorMemory
from services.memory import search_memories, search_memories_tagged, dedup_echoes, remember_structured_event, run_cognify
from services.llm_client import generate_chat_completion, parse_json_response

# Probability that a new Situation/Rumor is even ALLOWED to chain onto a recent one.
# Two forces balance here: without any gate the LLM chains almost every turn, but the
# old 35% gate (compounded by the LLM's own reluctance when given discretion) made
# CONSEQUENCE chains so rare the Tapestry stayed a field of orphan roots. 65% eligible,
# with a guaranteed pass when the last situation was severe — catastrophes always echo.
SITUATION_CHAIN_PROBABILITY = 0.65
SEVERE_SITUATION_ALWAYS_CHAINS = 4  # last situation's severity >= this forces eligibility
RUMOR_EVOLVE_PROBABILITY = 0.5

async def generate_situation(db: Session, kingdom_id: int) -> Situation:
    kingdom = db.query(Kingdom).filter(Kingdom.id == kingdom_id).first()
    world_state = kingdom.world_state
    
    # 1. Fetch active adaptations
    active_adaptations_list = [a.display_name for a in kingdom.adaptations if a.status == "completed"]
    active_adaptations_str = ", ".join(active_adaptations_list) if active_adaptations_list else "None"
    
    # 2. Fetch SQL Context (Conscious Mind / Short-Term Memory)
    recent_events = db.query(HistoricalEvent).filter(HistoricalEvent.kingdom_id == kingdom_id).order_by(HistoricalEvent.id.desc()).limit(3).all()
    recent_events_str = "\n".join([f"- {e.description}" for e in recent_events]) if recent_events else "No recent events."

    # Recent situations WITH their IDs, so the LLM can reference a REAL parent for causal chaining.
    recent_situations = db.query(Situation).filter(Situation.kingdom_id == kingdom_id).order_by(Situation.id.desc()).limit(6).all()
    last_was_severe = bool(recent_situations) and (recent_situations[0].severity or 1) >= SEVERE_SITUATION_ALWAYS_CHAINS
    situation_chain_allowed = bool(recent_situations) and (last_was_severe or random.random() < SITUATION_CHAIN_PROBABILITY)
    valid_situation_ids = {s.id for s in recent_situations} if situation_chain_allowed else set()
    if recent_situations:
        recent_situations_str = "\n".join(
            f"- [Situation ID {s.id}] '{s.title}' ({s.season}, Yr {s.year}): {(s.narrative or '')[:140]}"
            for s in recent_situations
        )
    else:
        recent_situations_str = "No prior situations (this is the first — caused_by_situation_id MUST be null)."

    if situation_chain_allowed:
        situation_chain_instruction = (
            'STRONGLY PREFER making this situation a direct consequence of one of the above: pick the most '
            'narratively fertile recent situation (especially one the divine ignored, worsened, or resolved '
            'wrathfully) and let its aftermath become this new crisis. Set "caused_by_situation_id" to that '
            'EXACT Situation ID and land the causal thread in the narrative. Use null ONLY if no listed '
            'situation could plausibly have led to anything. Never invent an ID that is not listed here.'
        )
        caused_by_schema_hint = (
            'STRONGLY PREFERRED: one of the Situation IDs listed under "RECENT SITUATIONS" above. '
            'Null only if no listed situation could plausibly cause this. Never invent an ID.'
        )
    else:
        situation_chain_instruction = (
            'This situation MUST be a fresh, standalone event, unrelated to the situations above. Set '
            '"caused_by_situation_id" to null. Do NOT chain this event onto any prior situation, even if a '
            'connection seems narratively tempting.'
        )
        caused_by_schema_hint = 'MUST be null. This situation must be freestanding, not a consequence of any prior situation.'
    
    last_chronicle = db.query(ChronicleEntry).filter(ChronicleEntry.kingdom_id == kingdom_id).order_by(ChronicleEntry.id.desc()).first()
    chronicle_str = last_chronicle.summary if last_chronicle else "No history recorded yet."
    
    last_meeting = db.query(CouncilMeeting).filter(CouncilMeeting.kingdom_id == kingdom_id).order_by(CouncilMeeting.id.desc()).first()
    meeting_str = f"The Council last decided to authorize: {last_meeting.proposal}" if last_meeting else "The Council has not met yet."
    
    active_rumors = db.query(Rumor).filter(Rumor.kingdom_id == kingdom_id, Rumor.is_true == -1).all()
    rumor_evolve_allowed = bool(active_rumors) and random.random() < RUMOR_EVOLVE_PROBABILITY
    valid_rumor_ids = {r.id for r in active_rumors} if rumor_evolve_allowed else set()
    rumor_str = ", ".join([r.content for r in active_rumors]) if active_rumors else "No prominent rumors."

    if rumor_evolve_allowed:
        parent_rumor_hint = (
            "Int or null (If this new rumor directly evolves from a past retrieved rumor listed in "
            "Active Rumors above, provide its ID here. Otherwise null.)"
        )
    else:
        parent_rumor_hint = (
            "null (This rumor MUST be a brand-new, standalone whisper, not an evolution of any past rumor. Always null.)"
        )

    # 3. Targeted Cognee Interrogations (Subconscious / Long-Term Memory)
    # Each query returns track-tagged {"track","text"} echoes; we accumulate then dedup+cap
    # (dedup_echoes -> MAX_ECHOES) so the "Echoes of the Past" panel and the prompt both get a
    # small, labeled, non-repeating set instead of 30-90 raw chunks.
    semantic_echoes = []
    echoes = []

    try:
        # 1. Retrieve Dynamic Adaptation & Resilience History
        if kingdom.food < 30:
            adapt_mem = await search_memories_tagged("What past situations caused famine or starvation, and what adaptations did the Council build to prevent them?", ["kingdom_history"])
        elif kingdom.realm_unrest > 60:
            adapt_mem = await search_memories_tagged("How did the kingdom resolve past unrest or riots, and what structures were built to maintain order?", ["kingdom_history"])
        else:
            adapt_mem = await search_memories_tagged("What adaptations has the kingdom built to survive calamities, and what specific vulnerabilities do they protect against?", ["kingdom_history"])

        if adapt_mem: semantic_echoes.extend(adapt_mem)

        # 2. Retrieve Causality Chains
        cause_mem = await search_memories_tagged(
            f"What past situations caused lingering consequences that could trigger a new crisis today in {kingdom.name}?",
            ["kingdom_history"]
        )
        if cause_mem: semantic_echoes.extend(cause_mem)

        # 3. Check for Divine Suspicion (The Paranoia Arc)
        divine_mem = await search_memories_tagged(
            "Which elders suspect that a divine, unseen power is manipulating the kingdom, and what did they observe?",
            ["rumor_history", "elder_history"]
        )
        if divine_mem: semantic_echoes.extend(divine_mem)

        # Threshold: Unrest
        if kingdom.realm_unrest > 60:
            unrest_mem = await search_memories_tagged("Which elders opposed recent adaptations or fueled dissent?", ["elder_history"])
            if unrest_mem: semantic_echoes.extend(unrest_mem)

        # Threshold: Trust
        trust_mem = await search_memories_tagged("What rumors, folklore, or paranoid legends are circulating among the commoners?", ["rumor_history"])
        if trust_mem: semantic_echoes.extend(trust_mem)

        # Threshold: Weather / Disasters
        if kingdom.weather != "Clear" or kingdom.consecutive_disasters > 1:
            disaster_mem = await search_memories_tagged("How has the kingdom historically suffered or adapted to nature's wrath?", ["disaster_history"])
            if disaster_mem: semantic_echoes.extend(disaster_mem)

        # Threshold: High Food (Prosperity) -> External world
        if kingdom.food > 70:
            world_mem = await search_memories_tagged("What external forces, merchants, or kingdoms are looking to trade or invade?", ["external_world_history"])
            if world_mem: semantic_echoes.extend(world_mem)

        echoes = dedup_echoes(semantic_echoes)
        cognee_memories_str = "\\n".join(f"[{e['track']}] {e['text']}" for e in echoes) if echoes else "None"
    except Exception as e:
        print(f"[Warning] Failed to fetch targeted Cognee memories: {e}")
        echoes = []
        cognee_memories_str = "None"
        
    # 4. Fetch Elders context
    elders = db.query(Elder).filter(Elder.kingdom_id == kingdom_id).all()
    elders_context = []
    for elder in elders:
        elders_context.append(f"- {elder.name} ({elder.role}): Belief {elder.belief_in_divine}/100, Mood: {elder.mood}")
    elders_context_str = "\n".join(elders_context)
        
    # 5. Build context
    context = f"""
You are the Engine of History for a medieval god-simulator game. 
Your purpose is to generate the next Situation for the kingdom of {kingdom.name}. 
The player is the invisible god they worship.

=== CURRENT STATE ===
Time: Year {kingdom.current_year}, {kingdom.current_season}
Resources: Food: {kingdom.food}/100 | Faith: {kingdom.faith}/100
Tension: Unrest: {kingdom.realm_unrest}/100 | Trust in Rulers: {kingdom.trust_in_ruling_class}/100
Divine Influence (Mana): {kingdom.divine_influence}/{kingdom.divine_influence_max}
Morale: {kingdom.current_morale}/100 (0 = Total Hope, 100 = Absolute Despair)
Atmosphere: Weather: {kingdom.weather} | Omen: {kingdom.omen_active or 'None'}

=== POPULATION MOOD ===
{world_state.population_mood_json}
(Let the highest mood dictate the tone of the crowd in your narrative).

=== COUNCIL OF ELDERS ===
{elders_context_str}

=== RECENT HISTORY & MEMORIES ===
Immediate Past (SQL):
{recent_events_str}

=== RECENT SITUATIONS (canonical IDs for causal chaining) ===
{recent_situations_str}
({situation_chain_instruction})

Latest Chronicle: {chronicle_str}
Last Council Decision: {meeting_str}
Active Rumors: {rumor_str}

=== KINGDOM INTELLIGENCE (COGNEE MEMORY) ===
{cognee_memories_str}

CRITICAL INSTRUCTION FOR ADAPTATIONS: 
If the Kingdom Intelligence indicates that an active adaptation was historically built to handle a crisis similar to the one you are generating, the adaptation MUST mitigate the damage. You must explicitly acknowledge the adaptation's success in the narrative, and reduce the severity of the crisis. Do not ignore the kingdom's past intelligence.


Active Adaptations: {active_adaptations_str}

(Important: The narrative of this new situation MUST logically follow the Immediate Past and Semantic Memories. If this situation is a consequence of a past event, you MUST explicitly explain the causal journey in the narrative. Remind the player of their past actions or the historical event that triggered this chain reaction.)
(Critical: The Elders might slowly begin to suspect that their lives are being manipulated by a higher power (you). Use their changing moods and beliefs to reflect this creeping realization or paranoid devotion in the narrative, based on their deep history grudges and their traits.)
CRITICAL INSTRUCTION (FOLKLORE): If the retrieved Semantic Memories contain past Rumors, you must attempt to fuse them together into a terrifying new Legend. If the category of this situation is 'Mystery' or 'Religion', the crisis MUST be the culmination of those past rumors evolving into a real threat (e.g., a witch hunt, a cult uprising, or the discovery of a fabled beast).

=== TASK ===
{"Generate the next crisis or opportunity — ideally one that grows out of the recent situations above, so the kingdom's history visibly compounds." if situation_chain_allowed else "Generate a new, unexpected crisis or opportunity, unrelated to the recent situations above."}
1. VOICE: Wry medieval chronicler, not a bard mid-eulogy. Think dry gallows humor, absurd specificity, deadpan understatement — the stakes are real but the telling should have a smirk in it. The narrative tone must still match the Morale and highest Population Mood (a despairing kingdom doesn't get slapstick, but it can get dark wit).
2. LENGTH: Max 2 short paragraphs, 4-6 sentences total. Cut every sentence that doesn't either move the plot or land a joke. No throat-clearing, no "the sun rose over the land" scene-setting — open on the problem.
3. Provide exactly 4 interventions. 'Cost' represents Divine Influence (Mana).
   - Option 1: A direct, benevolent miracle (High cost > 0, deducts Mana, high positive impact).
   - Option 2: A subtle nudge, empowering mortals or nature (Medium cost > 0, deducts Mana).
   - Option 3: An EVIL, wrathful, or sacrificial choice (e.g. smiting, plague, blood sacrifice). This must have a NEGATIVE cost (e.g., -20) to GENERATE Mana for the player, but it must cause massive harm or unrest. Fear fuels power.
   - Option 4: "Do nothing." Let the mortals handle it (Cost 0, usually negative/unpredictable effects).

Return ONLY valid JSON in this exact structure, with no markdown wrappers or extra text.

{{
    "title": "String, max 6 words (e.g., 'The River Runs Dry')",
    "narrative": "String, max 2 short paragraphs (4-6 sentences total). Wry, punchy, specific. Open on the problem, not the weather. CRITICAL: If this is a consequence of a past situation, briefly land the causal thread in one line rather than re-telling the whole history. Mention how the people are reacting based on their Mood, in one sharp beat rather than a paragraph.",
    "category": "Nature | Society | Economy | Religion | Infrastructure | Mystery",
    "severity": Int (1-5, where 1 is flavor and 5 is an existential threat),
    "caused_by_situation_id": Int or null ({caused_by_schema_hint}),
    "interventions": [
        {{
            "_rationale": "String, your internal reasoning for why these effects make logical and narrative sense. (Hidden from player)",
            "description": "String, an actionable command (e.g., 'Summon a sudden, torrential rain')",
            "cost": Int (-50 to {kingdom.divine_influence_max}. Positive deducts Mana, negative generates Mana),
            "overall_impact": "none | minor_boost | boost | major_boost | miracle | divine | minor_harm | harm | major_harm | catastrophe | apocalyptic",
            "effects": {{
                "food": "none | minor_boost | boost | major_boost | miracle | divine | minor_harm | harm | major_harm | catastrophe | apocalyptic",
                "faith": "none | minor_boost | boost | major_boost | miracle | divine | minor_harm | harm | major_harm | catastrophe | apocalyptic",
                "unrest": "none | minor_boost | boost | major_boost | miracle | divine | minor_harm | harm | major_harm | catastrophe | apocalyptic",
                "morale": "none | minor_boost | boost | major_boost | miracle | divine | minor_harm | harm | major_harm | catastrophe | apocalyptic",
                "trust": "none | minor_boost | boost | major_boost | miracle | divine | minor_harm | harm | major_harm | catastrophe | apocalyptic"
            }},
            "atmosphere_effects": {{
                "weather": "Clear | Rain | Storm | Drought | Fog | unchanged",
                "omen": "None | Blood Moon | Comet | Eclipse | unchanged"
            }},
            "mood_effects": {{
                "hopeful": Int (-20 to 20),
                "fearful": Int (-20 to 20),
                "angry": Int (-20 to 20),
                "devoted": Int (-20 to 20)
            }},
            "elder_effects": {{
                "Aldric": {{ "belief": Int (-20 to 20), "mood": "Neutral | Angry | Fearful | Hopeful | Grieving | unchanged" }},
                "Rowan": {{ "belief": Int (-20 to 20), "mood": "Neutral | Angry | Fearful | Hopeful | Grieving | unchanged" }},
                "Tomas": {{ "belief": Int (-20 to 20), "mood": "Neutral | Angry | Fearful | Hopeful | Grieving | unchanged" }},
                "Martha": {{ "belief": Int (-20 to 20), "mood": "Neutral | Angry | Fearful | Hopeful | Grieving | unchanged" }},
                "Elric": {{ "belief": Int (-20 to 20), "mood": "Neutral | Angry | Fearful | Hopeful | Grieving | unchanged" }}
            }}
        }}
    ],
    "new_rumor": {{
        "rumor_text": "String (A paranoid or superstitious whisper spreading among the commoners about this crisis)",
        "target": "String (Who or what the rumor is about, e.g. 'Tomas', 'The River', 'The Unseen Hand')",
        "parent_rumor_id": "{parent_rumor_hint}"
    }}
}}
"""
    messages = [{"role": "system", "content": context}]
    
    raw_response = generate_chat_completion(messages)

    try:
        data = parse_json_response(raw_response)
    except Exception as e:
        print(f"[Situation Engine] Failed to parse JSON. Error: {e}. Falling back.")
        # Fallback situation
        data = {
            "title": "A Quiet Season",
            "narrative": "The season shifts quietly. The winds are calm and the people tend to their daily tasks. Yet, unease still lingers beneath the surface.",
            "category": "Society",
            "severity": 1,
            "interventions": [
                {
                    "_rationale": "Fallback option",
                    "description": "Whisper comforting omens",
                    "cost": 10,
                    "overall_impact": "minor_boost",
                    "effects": {"faith": "minor_boost", "unrest": "minor_harm", "morale": "harm", "trust": "minor_boost", "food": "none"},
                    "atmosphere_effects": {"weather": "unchanged", "omen": "unchanged"},
                    "mood_effects": {"hopeful": 10, "fearful": -10, "angry": -5, "devoted": 5},
                    "elder_effects": {
                        "Aldric": {"belief": 5, "mood": "Hopeful"},
                        "Rowan": {"belief": 0, "mood": "unchanged"},
                        "Tomas": {"belief": 0, "mood": "unchanged"},
                        "Martha": {"belief": 0, "mood": "unchanged"},
                        "Elric": {"belief": 0, "mood": "unchanged"}
                    }
                },
                {
                    "_rationale": "Fallback option",
                    "description": "Do nothing",
                    "cost": 0,
                    "overall_impact": "none",
                    "effects": {"unrest": "none", "morale": "minor_boost", "trust": "none", "food": "none", "faith": "none"},
                    "atmosphere_effects": {"weather": "unchanged", "omen": "unchanged"},
                    "mood_effects": {"hopeful": 0, "fearful": 0, "angry": 0, "devoted": 0},
                    "elder_effects": {
                        "Aldric": {"belief": 0, "mood": "unchanged"},
                        "Rowan": {"belief": 0, "mood": "unchanged"},
                        "Tomas": {"belief": 0, "mood": "unchanged"},
                        "Martha": {"belief": 0, "mood": "unchanged"},
                        "Elric": {"belief": 0, "mood": "unchanged"}
                    }
                }
            ]
        }
        
    # Validate the causal link: only accept an ID that actually exists for this kingdom,
    # otherwise store null (a hallucinated/stale ID would silently orphan the node into a root).
    parent_situation_id = data.get("caused_by_situation_id")
    if not isinstance(parent_situation_id, int) or parent_situation_id not in valid_situation_ids:
        parent_situation_id = None

    situation = Situation(
        kingdom_id=kingdom.id,
        title=data.get("title", "Unknown Event"),
        narrative=data.get("narrative", ""),
        category=data.get("category", "Nature"),
        severity=data.get("severity", 1),
        parent_situation_id=parent_situation_id,
        season=kingdom.current_season,
        year=kingdom.current_year,
        interventions_json=json.dumps(data.get("interventions", [])),
        retrieved_memories_json=json.dumps(echoes) if echoes else None
    )
    db.add(situation)
    db.commit()
    db.refresh(situation)
    
    # Process New Rumor
    new_rumor_data = data.get("new_rumor")
    if new_rumor_data:
        try:
            parent_id = new_rumor_data.get("parent_rumor_id")
            if parent_id == "null" or not isinstance(parent_id, int) or parent_id not in valid_rumor_ids:
                parent_id = None
                
            new_rumor_sql = Rumor(
                kingdom_id=kingdom.id,
                content=new_rumor_data.get("rumor_text", "Whispers in the dark."),
                source_elder="Commoners",
                is_true=-1,
                spread=30,
                created_season=kingdom.current_season,
                created_year=kingdom.current_year,
                parent_rumor_id=parent_id
            )
            db.add(new_rumor_sql)
            db.commit()
            db.refresh(new_rumor_sql)
            
            rumor_mem = RumorMemory(
                originating_situation=situation.title,
                rumor_text=new_rumor_sql.content,
                target=new_rumor_data.get("target", "Unknown"),
                parent_rumor_id=new_rumor_sql.parent_rumor_id,
                season=kingdom.current_season,
                year=kingdom.current_year
            )
            
            await remember_structured_event(rumor_mem, "rumor_history")
            # We omit run_cognify here to avoid latency during gameplay loops. 
            # It will be naturally batched at the end of the next Council Meeting.
        except Exception as e:
            print(f"[Warning] Failed to stage new rumor: {e}")
            
    return situation
