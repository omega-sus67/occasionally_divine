# Unrest level at which the Council of Elders convenes. Checked at the unrest PEAK
# (right after intervention effects apply, before seasonal drift) — the old check ran
# after drift against >= 100, a value the drift made unreachable, so the council
# never fired. After a council resolves, unrest is vented below this threshold
# (see council/engine.py) so the council can't re-summon every single turn.
COUNCIL_UNREST_THRESHOLD = 70

IMPACT_MAP = {
    "none": 0,
    # Positive Impacts
    "minor_boost": 5,
    "boost": 10,
    "major_boost": 20,
    "miracle": 45,
    "divine": 60,
    # Negative Impacts
    "minor_harm": -5,
    "harm": -10,
    "major_harm": -20,
    "catastrophe": -45,
    "apocalyptic": -60
}

def parse_llm_effects(raw_effects: dict, overall_impact: str) -> dict:
    """
    Sanitizes and normalizes the LLM's generated effects using Severity Adjectives.
    Falls back to the overall_impact if a specific stat is hallucinated.
    """
    clean_effects = {}
    valid_keys = ["food", "faith", "unrest", "morale", "trust"]
    
    # Normalize overall_impact to get the fallback integer
    fallback_val = IMPACT_MAP.get(str(overall_impact).lower().strip(), 0)
    
    for key in valid_keys:
        if key in raw_effects:
            raw_val = str(raw_effects[key]).lower().strip()
            if raw_val in IMPACT_MAP:
                clean_effects[key] = IMPACT_MAP[raw_val]
            else:
                # Hallucination detected! Use the intelligent fallback.
                clean_effects[key] = fallback_val
        else:
            clean_effects[key] = 0
            
    return clean_effects
