from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from models.domain import Kingdom, HistoricalEvent, CouncilMeeting, Adaptation, ChronicleEntry, Elder, Rumor, Situation
from models.cognee_schemas import SituationMemory, ElderActionMemory, SuspectDivineMemory, AdaptationMemory, InterElderRelationMemory
from services.memory import search_memories, search_memories_tagged, dedup_echoes, remember_event, run_cognify, remember_structured_event, get_elder_stances_on_topic
from services.llm_client import generate_chat_completion, parse_json_response
from services.utils import parse_llm_effects, COUNCIL_UNREST_THRESHOLD
from prompts.council import COUNCIL_SYSTEM_PROMPT, build_council_user_prompt

async def run_council_meeting(db: Session, kingdom_id: int) -> dict:
    kingdom = db.query(Kingdom).filter(Kingdom.id == kingdom_id).first()
    if not kingdom:
        return {"status": "error", "message": "Kingdom not found."}

    # 1. Gather Short-Term SQL Context
    recent_events = db.query(HistoricalEvent).filter(
        HistoricalEvent.kingdom_id == kingdom_id
    ).order_by(HistoricalEvent.id.desc()).limit(5).all()
    events_list = [e.description for e in recent_events]
    
    active_rumors = db.query(Rumor).filter(Rumor.kingdom_id == kingdom_id, Rumor.is_true == -1).all()
    rumor_str = ", ".join([r.content for r in active_rumors]) if active_rumors else "No prominent rumors."

    # 2. Gather Elders State
    elders = db.query(Elder).filter(Elder.kingdom_id == kingdom_id).all()
    elders_context = []
    for elder in elders:
        elders_context.append(f"- {elder.name} ({elder.role}): Belief {elder.belief_in_divine}/100, Mood: {elder.mood}")
    elders_context_str = "\\n".join(elders_context)

    # 3. Gather Context from Cognee (Deep History)
    # Track-tagged {"track","text"} echoes, accumulated then deduped+capped (dedup_echoes ->
    # MAX_ECHOES) so "Recalled from the Tapestry" and the debate prompt get a small, labeled,
    # non-repeating set rather than the full 6-query chunk dump.
    semantic_memories = []
    try:
        base_mem = await search_memories_tagged(f"What are the most pressing threats or recent disasters in {kingdom.name}?", ["kingdom_history"])
        if base_mem: semantic_memories.extend(base_mem)

        current_crisis = events_list[0] if events_list else "the current crisis"
        adapt_mem = await search_memories_tagged(f"The council is debating how to solve '{current_crisis}'. What adaptations were built in the past to solve similar calamities, and who supported them?", ["kingdom_history"])
        if adapt_mem: semantic_memories.extend(adapt_mem)

        elder_mem = await get_elder_stances_on_topic(events_list[0] if events_list else kingdom.name)
        if elder_mem: semantic_memories.append({"track": "Elder", "text": f"Elder historical stances: {elder_mem}"})

        rumor_mem = await search_memories_tagged("What are the people whispering about right now? Do they suspect divine intervention?", ["rumor_history"])
        if rumor_mem: semantic_memories.extend(rumor_mem)

        external_mem = await search_memories_tagged("What external forces or merchants have interacted with us?", ["external_world_history"])
        if external_mem: semantic_memories.extend(external_mem)

        grudge_mem = await search_memories_tagged("What grudges, rivalries, or alliances currently exist between the elders?", ["relationship_history"])
        if grudge_mem: semantic_memories.extend(grudge_mem)

        # ── GRAPH TRACE: backward causality ──────────────────────────────────
        # find_causative_situation() walks the knowledge graph backward to trace
        # the root event that triggered this crisis. This is the clearest proof
        # that Cognee is doing non-trivial work: it surfaces *why* this meeting
        # was called, not just *that* it was called.
        from services.memory import find_causative_situation
        trace_result = await find_causative_situation(current_crisis)
        if trace_result and trace_result.get("raw_memory"):
            graph_trace = {"track": "Graph", "text": f"📜 GRAPH TRACE — Root cause retrieved from knowledge graph: {trace_result['raw_memory']}"}
            semantic_memories.insert(0, graph_trace)  # put it first so judges see it immediately
        # ─────────────────────────────────────────────────────────────────────

        # dedup_echoes preserves order, so the inserted GRAPH TRACE stays first.
        semantic_memories = dedup_echoes(semantic_memories)
        cognee_memories_str = "\\n".join(f"[{e['track']}] {e['text']}" for e in semantic_memories) if semantic_memories else "No deep memories found."
    except Exception as e:
        print(f"[Warning] Failed to fetch Cognee memories for council: {e}")
        semantic_memories = []
        cognee_memories_str = "No deep memories found."
        
    full_deep_history = f"Active Rumors: {rumor_str}\\nCognee Semantic Memories: {cognee_memories_str}"

    # 4. Construct prompt messages
    resources = {
        "food": kingdom.food,
        "faith": kingdom.faith,
        "population": kingdom.population,
        "unrest": kingdom.realm_unrest
    }
    
    system_msg = {"role": "system", "content": COUNCIL_SYSTEM_PROMPT}
    user_msg = {
        "role": "user",
        "content": build_council_user_prompt(kingdom.name, resources, events_list, full_deep_history, elders_context_str)
    }

    # 5. Generate LLM debate
    raw_response = generate_chat_completion([system_msg, user_msg])
    
    try:
        meeting_data = parse_json_response(raw_response)
    except Exception as e:
        print(f"[JSON Parse Error] Failed to parse council response: {e}. Raw: {raw_response}")
        meeting_data = {
            "discussion": [
                {"speaker": "Rowan", "dialogue": "We must adapt to survive. Let us build Drainage Canals."}
            ],
            "proposal": "Drainage Canals",
            "gameplay_effect_description": "Protects against floods.",
            "overall_impact": "minor_boost",
            "effects": {"food": "boost", "faith": "none", "unrest": "minor_harm", "morale": "minor_harm", "trust": "minor_boost"},
            "consequence_summary": "The elders agreed to build drainage networks after a messy debate."
        }

    proposal = meeting_data.get("proposal", "Drainage Canals")
    
    # 6. Create Council Meeting Record in DB
    meeting = CouncilMeeting(
        kingdom_id=kingdom_id,
        year=kingdom.current_year,
        season=kingdom.current_season,
        proposal=proposal
    )
    # Store the ENTIRE meeting data JSON so `resolve` can access the effects block
    meeting.set_discussion(meeting_data)
    # Persist the memories the elders "recalled" so the UI can render the graph made visible
    meeting.set_retrieved_memories(semantic_memories)
    db.add(meeting)
    db.commit()

    meeting_dict = meeting.to_dict()

    return {
        "status": "success",
        "meeting": meeting_dict,
        "proposal": proposal,
        "discussion": meeting_data.get("discussion", []),
        "retrieved_memories": semantic_memories,
        "gameplay_effect_description": meeting_data.get("gameplay_effect_description", ""),
        "dominant_emotion": meeting_data.get("dominant_emotion"),
        "consequence": meeting_data.get("consequence_summary")
    }

async def resolve_council_meeting(db: Session, kingdom_id: int, background_tasks: BackgroundTasks = None) -> dict:
    """
    Called when player accepts the adaptation.
    Applies adaptation, dynamic stat changes, writes chronicle, and records to Cognee.
    """
    kingdom = db.query(Kingdom).filter(Kingdom.id == kingdom_id).first()
    if not kingdom:
        return {"status": "error", "message": "Kingdom not found."}

    # Get latest meeting
    meeting = db.query(CouncilMeeting).filter(
        CouncilMeeting.kingdom_id == kingdom_id
    ).order_by(CouncilMeeting.id.desc()).first()

    if not meeting:
        return {"status": "error", "message": "No active council found."}

    proposal = meeting.proposal
    meeting_data = meeting.get_discussion()
    
    # Get the latest resolved situation to link this adaptation to
    latest_situation = db.query(Situation).filter(
        Situation.kingdom_id == kingdom_id
    ).order_by(Situation.id.desc()).first()
    
    situation_id = latest_situation.id if latest_situation else 0
    situation_title = latest_situation.title if latest_situation else "Unknown Calamity"
    resilience_focus = latest_situation.category if latest_situation else "General Calamity"
    
    if isinstance(meeting_data, dict):
        discussion = meeting_data.get("discussion", [])
        effects = meeting_data.get("effects", {})
        gameplay_effect = meeting_data.get("gameplay_effect_description", "Improves realm stability.")
        consequence_summary = meeting_data.get("consequence_summary", f"Constructed {proposal}.")
    else:
        # Legacy fallback if old meeting was generated
        discussion = meeting_data
        effects = {}
        gameplay_effect = "Improves realm stability."
        consequence_summary = f"Constructed {proposal}."

    overall_impact = meeting_data.get("overall_impact", "none") if isinstance(meeting_data, dict) else "none"

    # Apply dynamic stat changes from the LLM's 'effects' block
    parsed_effects = parse_llm_effects(effects, overall_impact)
    
    food_change = parsed_effects.get("food", 0)
    faith_change = parsed_effects.get("faith", 0)
    unrest_change = parsed_effects.get("unrest", 0)
    morale_change = parsed_effects.get("morale", 0)
    trust_change = parsed_effects.get("trust", 0)
    
    kingdom.food = max(0, min(100, kingdom.food + food_change))
    kingdom.faith = max(0, min(100, kingdom.faith + faith_change))
    # Apply the LLM's unrest change, then guarantee the act of being heard vents the mob:
    # a resolved council always leaves unrest safely below the summon threshold, so the
    # council can't re-summon itself on the very next turn regardless of what the LLM chose.
    kingdom.realm_unrest = max(20, min(100, kingdom.realm_unrest + unrest_change))
    kingdom.realm_unrest = min(kingdom.realm_unrest, COUNCIL_UNREST_THRESHOLD - 15)
    kingdom.current_morale = max(0, min(100, kingdom.current_morale + morale_change))
    kingdom.trust_in_ruling_class = max(0, min(100, kingdom.trust_in_ruling_class + trust_change))

    # Check for Shrine Upgrades (Win Condition)
    if "stone temple" in proposal.lower():
        kingdom.shrine_level = max(kingdom.shrine_level, 2)
    elif "cathedral of the heavens" in proposal.lower():
        kingdom.shrine_level = 3
        kingdom.game_status = "victory"

    # Check if adaptation already exists, if not, create it dynamically
    existing = db.query(Adaptation).filter(
        Adaptation.kingdom_id == kingdom_id,
        Adaptation.display_name == proposal
    ).first()

    if not existing:
        new_adaptation = Adaptation(
            kingdom_id=kingdom_id,
            display_name=proposal,
            gameplay_effect=gameplay_effect,
            resilience_focus=resilience_focus,
            constructed_year=kingdom.current_year,
            status="completed"  # Approved adaptations protect the kingdom immediately.
        )
        db.add(new_adaptation)

    # Write to Chronicle
    chronicle = ChronicleEntry(
        kingdom_id=kingdom_id,
        year=kingdom.current_year,
        season=kingdom.current_season,
        summary=consequence_summary,
        consequence=f"Constructed {proposal}. Changed Food by {food_change}, Faith by {faith_change}, Unrest by {unrest_change}."
    )
    db.add(chronicle)
    db.commit()

    # Commit memory to Cognee using Explicit Pydantic Schemas
    try:
        datasets_to_update = ["kingdom_history", "elder_history", "rumor_history"]
        
        # 1. Stage the main Situation 
        situation_memory = SituationMemory(
            situation_id=meeting.id,
            title=f"Council Meeting: {proposal}",
            resolution=consequence_summary,
            adaptation_built=proposal,
            unrest_change=unrest_change,
            food_change=food_change,
            season=kingdom.current_season,
            year=kingdom.current_year
        )
        await remember_structured_event(situation_memory, "kingdom_history")

        # 2. Stage Explicit Elder Actions
        for d in discussion:
            elder_name = d.get('speaker', 'Unknown')
            dialogue = d.get('dialogue', '')
            
            # Identify action type heuristically
            action_type = "DEBATED"
            dialogue_lower = dialogue.lower()
            if any(word in dialogue_lower for word in ["agree", "yes", "support", "must build", "let us build", "good"]):
                action_type = "SUPPORTED"
            elif any(word in dialogue_lower for word in ["no", "never", "cost", "waste", "foolish", "insufficient"]):
                action_type = "OPPOSED"
                
            elder_action = ElderActionMemory(
                elder_name=elder_name,
                action_type=action_type,
                target_concept=proposal,
                rationale=dialogue,
                season=kingdom.current_season,
                year=kingdom.current_year
            )
            await remember_structured_event(elder_action, "elder_history")
            
            # 3. Track suspicions of the Divine Player
            if any(word in dialogue_lower for word in ["divine", "power", "unseen", "manipulate", "test", "trial", "hand", "lord", "miracle"]):
                suspicion = SuspectDivineMemory(
                    elder_name=elder_name,
                    suspicion_level="Growing",
                    observation=dialogue,
                    season=kingdom.current_season,
                    year=kingdom.current_year
                )
                await remember_structured_event(suspicion, "rumor_history")
                
        # 4. Stage Adaptation memory linking the chain of situations
        adaptation_memory = AdaptationMemory(
            adaptation_name=proposal,
            solved_situation_id=situation_id,
            solved_situation_title=situation_title,
            gameplay_effect=gameplay_effect,
            resilience_focus=resilience_focus,
            season=kingdom.current_season,
            year=kingdom.current_year
        )
        await remember_structured_event(adaptation_memory, "kingdom_history")
        
        # 5. Stage Inter-Elder Relationships (Grudges/Alliances)
        if isinstance(meeting_data, dict) and "new_relationships" in meeting_data:
            new_relations = meeting_data.get("new_relationships", [])
            for rel in new_relations:
                try:
                    rel_mem = InterElderRelationMemory(
                        elder_from=rel.get("elder_from", "Unknown"),
                        elder_to=rel.get("elder_to", "Unknown"),
                        relation_type=rel.get("relation_type", "Grudge"),
                        reason=rel.get("reason", "A heated debate."),
                        intensity=int(rel.get("intensity", 5)),
                        season=kingdom.current_season,
                        year=kingdom.current_year
                    )
                    await remember_structured_event(rel_mem, "relationship_history")
                    if "relationship_history" not in datasets_to_update:
                        datasets_to_update.append("relationship_history")
                except Exception as e:
                    print(f"[Warning] Failed to stage new relationship: {e}")
        
        # A council meeting is a narratively-critical event: the new adaptation and any
        # grudges/alliances formed here are exactly what future situations query. Force an
        # immediate cognify so this data is retrievable next turn (the frequent
        # per-intervention path stays throttled to save cost).
        if background_tasks:
            background_tasks.add_task(run_cognify, datasets_to_update, True)
        else:
            await run_cognify(datasets_to_update, force=True)
    except Exception as e:
        print(f"[Warning] Cognee memory update failed: {e}")

    return {
        "status": "success",
        "adaptation": proposal,
        "effects_applied": effects,
        "kingdom": kingdom.to_dict()
    }
