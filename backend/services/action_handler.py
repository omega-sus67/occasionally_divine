import json
from datetime import datetime
from sqlalchemy.orm import Session
from models.domain import Kingdom, WorldState, PlayerAction, HistoricalEvent, Situation, Elder, ChronicleEntry
from services.simulation import simulate_season
from services.utils import parse_llm_effects, IMPACT_MAP, COUNCIL_UNREST_THRESHOLD
from data.minor_cards import resolve_minor_choice

from fastapi import BackgroundTasks

async def execute_intervention(db: Session, kingdom_id: int, situation_id: int, intervention_index: int, background_tasks: BackgroundTasks = None, minor_choices: dict = None) -> dict:
    kingdom = db.query(Kingdom).filter(Kingdom.id == kingdom_id).first()
    if not kingdom:
        return {"status": "error", "message": "Kingdom not found."}
        
    if kingdom.game_status != "active":
        return {"status": "error", "message": f"Game is over. Status: {kingdom.game_status}"}

    situation = db.query(Situation).filter(Situation.id == situation_id).first()
    if not situation:
        return {"status": "error", "message": "Situation not found."}

    try:
        interventions = json.loads(situation.interventions_json)
    except Exception:
        return {"status": "error", "message": "Invalid interventions data in situation."}

    if intervention_index < 0 or intervention_index >= len(interventions):
        return {"status": "error", "message": "Invalid intervention index."}
        
    intervention = interventions[intervention_index]

    cost = intervention.get("cost", 0)

    # --- Resolve minor-card choices (numeric only, no narrative weight) ---
    # Each drawn param may carry a {card_id, option_index}; resolve authoritatively
    # against the static pool so a tampered client can't inject arbitrary numbers.
    minor_effects = {"food": 0, "faith": 0, "unrest": 0, "morale": 0, "trust": 0}
    minor_cost = 0
    if minor_choices:
        for param, choice in minor_choices.items():
            if not isinstance(choice, dict):
                continue
            resolved = resolve_minor_choice(param, choice.get("card_id"), choice.get("option_index"))
            if resolved is None:
                continue  # unknown/invalid card — skip, don't fail the whole commit
            minor_effects[resolved["effect_key"]] += resolved["delta"]
            minor_cost += resolved["cost"]

    # Mana is a shared pool: the main intervention and every minor "good" choice spend
    # from it, while "evil" choices grant into it. Gate on the NET cost of the whole plan.
    total_cost = cost + minor_cost
    if total_cost > 0 and kingdom.divine_influence < total_cost:
        return {"status": "error", "message": f"Not enough Divine Influence. Need {total_cost}, have {kingdom.divine_influence}."}

    # Deduct net cost (if negative, it generates mana up to max; never below 0)
    kingdom.divine_influence = max(0, min(kingdom.divine_influence_max, kingdom.divine_influence - total_cost))
    
    # Save the chosen intervention string for history
    situation.chosen_intervention = intervention.get("description")
    
    # --- Apply Core Effects ---
    overall_impact = intervention.get("overall_impact", "none")
    raw_effects = intervention.get("effects", {})
    effects = parse_llm_effects(raw_effects, overall_impact)

    food_change = effects.get("food", 0)
    faith_change = effects.get("faith", 0)
    unrest_change = effects.get("unrest", 0)
    morale_change = effects.get("morale", 0)
    trust_change = effects.get("trust", 0)

    # --- Mechanically apply completed Adaptations ---
    # A completed adaptation whose resilience_focus matches this situation's category
    # dampens the harmful side of the LLM's effects, instead of relying on the LLM to
    # "remember" the adaptation from the prompt alone.
    MITIGATION_FACTOR = 0.5  # halves the damaging portion of the effect
    protective_adaptations = [
        a for a in kingdom.adaptations
        if a.status == "completed" and a.resilience_focus == situation.category
    ]
    if protective_adaptations:
        if food_change < 0:
            food_change = round(food_change * MITIGATION_FACTOR)
        if faith_change < 0:
            faith_change = round(faith_change * MITIGATION_FACTOR)
        if unrest_change > 0:
            unrest_change = round(unrest_change * MITIGATION_FACTOR)
        if morale_change > 0:
            morale_change = round(morale_change * MITIGATION_FACTOR)
        effects["food"] = food_change
        effects["faith"] = faith_change
        effects["unrest"] = unrest_change
        effects["morale"] = morale_change

    # Apply main effects + the piled minor-card deltas together (single clamp).
    # `effects`/`*_change` stay main-only below so the epilogue & memories never
    # mention the minor cards; minor_effects only moves the numbers.
    kingdom.food = max(0, min(100, kingdom.food + food_change + minor_effects["food"]))
    kingdom.faith = max(0, min(100, kingdom.faith + faith_change + minor_effects["faith"]))
    kingdom.realm_unrest = max(0, min(100, kingdom.realm_unrest + unrest_change + minor_effects["unrest"]))
    kingdom.current_morale = max(0, min(100, kingdom.current_morale + morale_change + minor_effects["morale"]))
    kingdom.trust_in_ruling_class = max(0, min(100, kingdom.trust_in_ruling_class + trust_change + minor_effects["trust"]))
    
    # --- Apply Atmosphere Effects ---
    atmosphere = intervention.get("atmosphere_effects", {})
    new_weather = atmosphere.get("weather", "unchanged")
    new_omen = atmosphere.get("omen", "unchanged")
    
    if new_weather != "unchanged":
        kingdom.weather = new_weather
    if new_omen != "unchanged":
        kingdom.omen_active = None if new_omen == "None" else new_omen
        
    # --- Apply Mood Effects ---
    mood_effects = intervention.get("mood_effects", {})
    if mood_effects:
        world_state = kingdom.world_state
        current_mood = world_state.get_mood()
        current_mood["hopeful"] = max(0, current_mood.get("hopeful", 0) + mood_effects.get("hopeful", 0))
        current_mood["fearful"] = max(0, current_mood.get("fearful", 0) + mood_effects.get("fearful", 0))
        current_mood["angry"] = max(0, current_mood.get("angry", 0) + mood_effects.get("angry", 0))
        current_mood["devoted"] = max(0, current_mood.get("devoted", 0) + mood_effects.get("devoted", 0))
        world_state.set_mood(current_mood)
        
    # --- Apply Elder Effects ---
    elder_effects = intervention.get("elder_effects", {})
    if elder_effects:
        elders = db.query(Elder).filter(Elder.kingdom_id == kingdom_id).all()
        elder_map = {e.name: e for e in elders}
        
        for e_name, e_changes in elder_effects.items():
            if e_name in elder_map:
                elder = elder_map[e_name]
                belief_change = e_changes.get("belief", 0)
                new_mood = e_changes.get("mood", "unchanged")
                
                elder.belief_in_divine = max(0, min(100, elder.belief_in_divine + belief_change))
                if new_mood != "unchanged":
                    elder.mood = new_mood
    
    # Record action history
    action_log = PlayerAction(
        kingdom_id=kingdom_id,
        action_type="Intervention",
        cost=cost,
        season=kingdom.current_season,
        year=kingdom.current_year,
        timestamp=datetime.utcnow().isoformat()
    )
    db.add(action_log)
    
    # Record historical event
    event_description = f"In Year {kingdom.current_year}, {kingdom.current_season}, a situation occurred: '{situation.title}'. The divine chose to: '{intervention.get('description')}'. "
    event_description += f"The overall impact was described as '{overall_impact}'. "
    if food_change != 0 or faith_change != 0 or unrest_change != 0:
        event_description += f"This shifted Food by {food_change}, Faith by {faith_change}, and Unrest by {unrest_change}. "
    if protective_adaptations:
        names = ", ".join(a.display_name for a in protective_adaptations)
        event_description += f"The kingdom's adaptation(s) ({names}) softened the blow, having been built for exactly this kind of crisis. "

    # Map the overall_impact word to a severity (1-5 range roughly)
    impact_val = abs(IMPACT_MAP.get(str(overall_impact).lower().strip(), 5))
    mapped_severity = max(1, min(5, impact_val // 10))
        
    event = HistoricalEvent(
        kingdom_id=kingdom_id,
        type="Situation Resolved",
        season=kingdom.current_season,
        year=kingdom.current_year,
        description=event_description,
        severity=mapped_severity,
        category=situation.category
    )
    # Save the full intervention payload for history, plus the minor-card deltas as a
    # numeric-only sub-record (no narrative — the description above ignores them).
    event.set_effects({**intervention, "minor_effects": minor_effects})
    db.add(event)
    
    # Check Loss Condition: Shrine Destroyed
    if kingdom.realm_unrest >= 80 and kingdom.faith <= 20:
        kingdom.game_status = "defeat"
        loss_entry = ChronicleEntry(
            kingdom_id=kingdom.id,
            year=kingdom.current_year,
            season=kingdom.current_season,
            summary="The mob, fueled by unbearable unrest and lacking any fear of the Divine, tore down the Shrine. We are forgotten."
        )
        db.add(loss_entry)
        
    # Council check happens HERE, at the unrest peak — before seasonal drift cools it.
    # (The old check ran after drift against >= 100, which drift made unreachable.)
    council_summoned = kingdom.realm_unrest >= COUNCIL_UNREST_THRESHOLD and kingdom.game_status == "active"

    # Advance time always after a situation is resolved
    epilogue = await simulate_season(db, kingdom, intervention.get("description", ""), effects)
    situation.epilogue = epilogue
    
    db.commit()
    
    # Commit memory to Cognee knowledge graph
    try:
        from services.memory import remember_event, remember_structured_event, run_cognify
        from models.cognee_schemas import SituationMemory
        datasets_to_update = {"kingdom_history"}

        # Structured causal memory: records this situation WITH its ID and its parent's ID,
        # so future situation generation can retrieve real IDs and chain events together.
        parent_title = None
        if situation.parent_situation_id:
            parent = db.query(Situation).filter(Situation.id == situation.parent_situation_id).first()
            parent_title = parent.title if parent else None

        situation_memory = SituationMemory(
            situation_id=situation.id,
            title=situation.title,
            resolution=intervention.get("description", "an unknown divine act"),
            caused_by_situation_id=situation.parent_situation_id,
            caused_by_situation_title=parent_title,
            unrest_change=unrest_change,
            food_change=food_change,
            season=kingdom.current_season,
            year=kingdom.current_year,
        )
        await remember_structured_event(situation_memory, "kingdom_history")

        await remember_event(event_description, "kingdom_history")

        if elder_effects:
            elder_desc = f"During '{situation.title}', the divine action '{intervention.get('description')}' affected the elders: "
            elder_desc += ", ".join([f"{name} ({changes.get('mood', 'unchanged')} mood, {changes.get('belief', 0)} belief)" for name, changes in elder_effects.items()])
            await remember_event(elder_desc, "elder_history")
            datasets_to_update.add("elder_history")
            
        if new_weather != "unchanged" or new_omen != "unchanged":
            weather_desc = f"In Year {kingdom.current_year}, {kingdom.current_season}, during '{situation.title}', the weather shifted to {new_weather} and omen to {new_omen}."
            await remember_event(weather_desc, "disaster_history")
            datasets_to_update.add("disaster_history")
            
        if mood_effects:
            mood_str = ", ".join([f"{k} by {v}" for k, v in mood_effects.items()])
            mood_desc = f"The divine action '{intervention.get('description')}' caused the population mood to shift: {mood_str}. Unrest shifted by {unrest_change}."
            await remember_event(mood_desc, "rumor_history")
            datasets_to_update.add("rumor_history")
            
        if background_tasks:
            background_tasks.add_task(run_cognify, list(datasets_to_update))
        else:
            await run_cognify(list(datasets_to_update))
    except Exception as e:
        print(f"[Warning] Cognee memory update failed: {e}")
    
    return {
        "status": "success",
        "description": event_description,
        "epilogue": epilogue,
        "effects_applied": intervention,
        "parsed_effects": effects,
        "minor_effects": minor_effects,
        "minor_cost": minor_cost,
        "mitigated_by": [a.display_name for a in protective_adaptations],
        "council_summoned": council_summoned,
        "event_id": event.id,
        "kingdom": kingdom.to_dict()
    }
