import random
from models.domain import Kingdom, WorldState, Adaptation, HistoricalEvent

from services.llm_client import generate_chat_completion
import asyncio

SEASONS = ["Spring", "Summer", "Autumn", "Winter"]

async def simulate_season(db, kingdom: Kingdom, intervention_desc: str, stat_changes: dict) -> str:
    """
    Advances the season, applies passive drift, and generates a narrative epilogue.
    """
    current_idx = SEASONS.index(kingdom.current_season)
    next_idx = (current_idx + 1) % len(SEASONS)
    kingdom.current_season = SEASONS[next_idx]
    
    if kingdom.current_season == "Spring":
        kingdom.current_year += 1

    # Regenerate influence
    kingdom.divine_influence = min(
        kingdom.divine_influence_max,
        kingdom.divine_influence + 15
    )

    # Apply passive drift
    drift_food = -5
    drift_unrest = -3
    drift_faith = -2
    
    kingdom.food = max(0, min(100, kingdom.food + drift_food))
    kingdom.realm_unrest = max(0, min(100, kingdom.realm_unrest + drift_unrest))
    kingdom.faith = max(0, min(100, kingdom.faith + drift_faith))
    
    # Population drift
    if kingdom.food > 50:
        kingdom.population += 50
    elif kingdom.food < 15:
        kingdom.population = max(0, kingdom.population - 50)
        
    # Build prompt for Epilogue
    active_adaptations = [a.display_name for a in kingdom.adaptations if a.status == "completed"]
    adaptations_str = ", ".join(active_adaptations) if active_adaptations else "None"
    
    prompt = f"""
    You are the invisible historian of the kingdom of {kingdom.name}.
    The season has shifted to {kingdom.current_season}, Year {kingdom.current_year}.
    
    The player (the divine entity) just took this action: "{intervention_desc}"
    This had the following immediate effects: {stat_changes}
    
    Additionally, time has passed. The people consumed food (Food -5), anger naturally cooled a bit (Unrest -3), and without constant miracles, doubt crept in (Faith -2).
    The kingdom currently has these active adaptations built: {adaptations_str}.
    
    Write a punchy 2-3 sentence epilogue, dry wit over purple prose, weaving together the divine intervention, the passing of time, and the active adaptations. One vivid image beats three vague ones. Do not list numbers, do not open with "As the season turned" or similar throat-clearing — start mid-scene.
    """
    
    try:
        messages = [{"role": "user", "content": prompt}]
        epilogue = generate_chat_completion(messages)
    except Exception as e:
        print(f"[Simulation Error] Epilogue generation failed: {e}")
        epilogue = f"The season turned to {kingdom.current_season}. The winds shifted, and time marched on."
        
    return epilogue

def check_win_lose(kingdom: Kingdom):
    """
    Returns 'win', 'lose', or None
    """
    if kingdom.faith <= 0 or kingdom.population <= 0:
        return 'lose'
    if kingdom.current_year > 5:
        return 'win'
    return None
