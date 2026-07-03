"""
Minor per-parameter cards — the small "plan your season" layer that sits alongside
the main Situation each turn.

Each turn, 2-3 of the five parameters are drawn at random and each gets ONE card
selected at random from that parameter's pool. Every card offers three interventions
following the same archetype as the main situation engine:

    - "good"    : nudges the parameter favourably, but COSTS divine influence (mana)
    - "evil"    : nudges it unfavourably, but GRANTS mana
    - "nothing" : no effect, no mana

These are hand-authored templates (zero LLM cost). `delta` is applied to the card's
OWN parameter with the correct sign (favourable = negative for unrest/despair, since
lower is better for those). `cost` is mana: positive spends, negative grants, 0 nothing.

The pool is the single source of truth: the client only echoes back a card_id +
option_index, and `resolve_minor_choice` re-validates against this file so a tampered
client cannot inject arbitrary numbers.
"""
import random

# Card param name -> the effect-dict key used by parse_llm_effects / execute_intervention.
# (UI/user say "despair"; the backend column is current_morale, whose effect key is "morale".)
PARAM_TO_EFFECT_KEY = {
    "food": "food",
    "faith": "faith",
    "unrest": "unrest",
    "despair": "morale",
    "trust": "trust",
}
PARAMS = list(PARAM_TO_EFFECT_KEY.keys())


def _card(card_id, title, text, good_label, good_delta, good_cost,
          evil_label, evil_delta, evil_cost, nothing_label="Let it pass"):
    """Small helper so the pool below stays readable. Enforces the good/evil/nothing archetype."""
    return {
        "id": card_id,
        "title": title,
        "text": text,
        "options": [
            {"kind": "good", "label": good_label, "delta": good_delta, "cost": good_cost},
            {"kind": "evil", "label": evil_label, "delta": evil_delta, "cost": evil_cost},
            {"kind": "nothing", "label": nothing_label, "delta": 0, "cost": 0},
        ],
    }


# For food/faith/trust: favourable delta is POSITIVE. Good costs mana; evil grants mana.
# For unrest/despair: favourable delta is NEGATIVE (lower is better). Good still costs mana.
MINOR_CARDS = {
    "food": [
        _card("good_catch", "A Good Catch", "Fishers return with brimming nets and ask for a blessing.",
              "Bless the waters", +3, 6, "Let the smugglers buy it cheap", -2, -5),
        _card("granary_mice", "Mice in the Granary", "Vermin gnaw at the winter stores.",
              "Send blessed cats", +2, 5, "Blame the poor and seize their grain", -3, -6),
        _card("orchard_bloom", "An Early Bloom", "The orchards flower a season too soon.",
              "Coax a gentle warmth", +4, 8, "Strip the branches bare for wine", -2, -4),
        _card("wandering_herd", "A Wandering Herd", "Wild cattle stray near the village fences.",
              "Guide them to the pens", +3, 7, "Slaughter them all at once", -1, -3),
        _card("failing_well", "The Failing Well", "The old well runs thin and brown.",
              "Sweeten the spring", +2, 5, "Ration water, hoard the rest", -3, -6),
    ],
    "faith": [
        _card("weeping_icon", "The Weeping Icon", "A shrine statue is said to weep at dawn.",
              "Sanctify the miracle", +3, 7, "Declare it a cheap trick", -3, -6),
        _card("lost_pilgrims", "Lost Pilgrims", "Travellers seek the shrine but lose the road.",
              "Light the way with an omen", +2, 5, "Let them wander and forget", -2, -4),
        _card("young_zealot", "A Young Zealot", "A fervent youth preaches in the square.",
              "Bless their sermon", +4, 8, "Silence them for heresy", -2, -5),
        _card("faded_hymn", "The Faded Hymn", "An old prayer is slipping from memory.",
              "Return it in a dream", +3, 6, "Let the silence grow", -1, -3),
        _card("doubting_priest", "The Doubting Priest", "A tired cleric questions the divine.",
              "Restore their conviction", +2, 5, "Feed their doubt", -3, -6),
    ],
    "unrest": [
        _card("tavern_brawl", "A Tavern Brawl", "Drink and grievance spill into the street.",
              "Cool the tempers", -3, 6, "Let them bleed each other", +2, -5),
        _card("market_quarrel", "A Market Quarrel", "Merchants and buyers come to blows over prices.",
              "Whisper fairness", -2, 5, "Take a cut of the chaos", +3, -6),
        _card("night_whispers", "Night Whispers", "Seditious talk moves house to house after dark.",
              "Send a calming dream", -4, 8, "Amplify the fear", +2, -4),
        _card("bread_line", "The Bread Line", "A queue at the granary grows short-tempered.",
              "Multiply the loaves", -3, 7, "Let them shove and shout", +1, -3),
        _card("mocked_guard", "The Mocked Guard", "The watch is jeered as it patrols.",
              "Restore their dignity", -2, 5, "Turn the crowd crueler", +3, -6),
    ],
    "despair": [
        _card("grey_morning", "A Grey Morning", "A heaviness hangs over the waking village.",
              "Send a warm sunrise", -3, 6, "Let the grey deepen", +2, -5),
        _card("empty_chair", "The Empty Chair", "A family mourns one lost to the winter.",
              "Comfort them in a vision", -2, 5, "Leave the grief to fester", +3, -6),
        _card("silent_bell", "The Silent Bell", "The festival bell has not rung in weeks.",
              "Ring it with unseen hands", -4, 8, "Let the silence smother hope", +2, -4),
        _card("faded_songs", "Faded Songs", "The children no longer sing at play.",
              "Return a joyful tune", -3, 7, "Let the quiet win", +1, -3),
        _card("long_night", "The Long Night", "The dark season wears on the spirit.",
              "Kindle small comforts", -2, 5, "Stretch the night longer", +3, -6),
    ],
    "trust": [
        _card("honest_steward", "An Honest Steward", "A minor official refuses a bribe openly.",
              "Reward their virtue", +3, 6, "Frame them as a fool", -2, -5),
        _card("tax_rumor", "The Tax Rumor", "Word spreads that the granary count was falsified.",
              "Reveal the honest ledger", +2, 5, "Let the suspicion grow", -3, -6),
        _card("public_pardon", "A Public Pardon", "A wronged farmer seeks justice at the gate.",
              "Grant a visible mercy", +4, 8, "Side quietly with the powerful", -2, -4),
        _card("shared_harvest", "The Shared Harvest", "The council debates sharing the surplus.",
              "Bless a fair division", +3, 7, "Let the lords keep it all", -1, -3),
        _card("broken_promise", "A Broken Promise", "A pledge to rebuild the mill was forgotten.",
              "Make the promise good", +2, 5, "Let it be forgotten", -3, -6),
    ],
}


def draw_minor_cards() -> list:
    """
    Draw 2-3 random parameters and one random card for each. Returns a list of
    dicts the frontend renders directly:
        [{"param", "id", "title", "text", "options": [{kind,label,delta,cost}, ...]}, ...]
    """
    chosen_params = random.sample(PARAMS, k=random.randint(2, 3))
    drawn = []
    for param in chosen_params:
        card = random.choice(MINOR_CARDS[param])
        drawn.append({
            "param": param,
            "id": card["id"],
            "title": card["title"],
            "text": card["text"],
            "options": [dict(opt) for opt in card["options"]],
        })
    return drawn


def resolve_minor_choice(param: str, card_id: str, option_index) -> dict | None:
    """
    Authoritatively resolve a client's minor-card choice against the static pool.
    Returns {"effect_key", "delta", "cost"} or None if anything is invalid
    (unknown param/card, out-of-range index) — the caller simply skips a None.
    """
    if param not in MINOR_CARDS:
        return None
    card = next((c for c in MINOR_CARDS[param] if c["id"] == card_id), None)
    if card is None:
        return None
    try:
        option = card["options"][int(option_index)]
    except (ValueError, TypeError, IndexError):
        return None
    return {
        "effect_key": PARAM_TO_EFFECT_KEY[param],
        "delta": int(option["delta"]),
        "cost": int(option["cost"]),
    }
