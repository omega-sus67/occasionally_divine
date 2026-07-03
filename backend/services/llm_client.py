import os
import re
import json
import litellm
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

# We use Gemini 2.5 Flash via LiteLLM for high-quality player-facing generation
MODEL_NAME = "gemini/gemini-2.5-flash"

def generate_chat_completion(messages: list) -> str:
    """
    Sends chat request to Gemini via LiteLLM.
    Falls back to a mockup response if API fails or key is missing.
    """
    try:
        # LiteLLM routes the request to local Ollama based on the model name prefix
        response = litellm.completion(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
            print(f"[LLM Error] {e}. Using fallback.")
        
    # Fallback response simulating an elder debate and proposing a smart adaptation
    # We construct a mock JSON matching the requested structure
    fallback_data = {
        "discussion": [
            {
                "speaker": "Rowan",
                "dialogue": "We must gather. The skies have opened or fires have taken our homes. We cannot stand idle."
            },
            {
                "speaker": "Martha",
                "dialogue": "Our fields are damaged and the food stores are empty. If we don't build Drainage Canals, we will starve!"
            },
            {
                "speaker": "Tomas",
                "dialogue": "I agree. Simple soil won't hold. We must construct Drainage Canals immediately to direct future deluges."
            },
            {
                "speaker": "Aldric",
                "dialogue": "The heavens test us. We should pray, but drainage is a wise use of the stone. Let it be built."
            },
            {
                "speaker": "Elric",
                "dialogue": "Canals cost coin, but starving is more expensive. Let us build them."
            }
        ],
        "proposal": "Drainage Canals",
        "consequence_summary": "Constructed drainage networks across Edengrove's farmlands to protect from future floods."
    }
    return json.dumps(fallback_data)


def parse_json_response(raw_response: str) -> dict:
    """
    Parses a JSON object out of a raw LLM text response.

    Models are asked to return "ONLY valid JSON" but sometimes wrap it in markdown
    fences or add a stray sentence before/after. Rather than constraining generation
    with a JSON-mode response_format (which risks flattening creative prose — see
    council/situation prompts), this stays purely a parsing-side fix: strip markdown
    fences if present, then fall back to extracting the first balanced {...} block
    from anywhere in the text. Raises ValueError with the raw response attached so
    callers can log it before falling back to their own placeholder content.
    """
    cleaned = raw_response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.split("```json", 1)[1].split("```")[0].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.split("```", 1)[1].split("```")[0].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: scan for the first balanced {...} block anywhere in the text, in case
    # the model added commentary outside the JSON. Tracks whether we're inside a JSON
    # string (respecting escapes) so braces inside dialogue/narrative text — which these
    # prompts generate plenty of — don't throw off the depth count.
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not extract valid JSON from LLM response. Raw response: {raw_response!r}")
