import os
from dotenv import load_dotenv
load_dotenv()

os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "false"
os.environ["CACHING"] = "false"
os.environ["LLM_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
os.environ["EMBEDDING_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

import cognee
from cognee import visualize_graph
from cognee.modules.search.types import SearchType
from cognee.modules.data.exceptions import DatasetNotFoundError
import asyncio
import json
from pydantic import BaseModel

# Setup Cognee local providers
cognee.config.set_graph_database_provider("kuzu")
cognee.config.set_vector_db_provider("lancedb")

# Configure LLM to use Gemini Flash via cognee
cognee.config.set_llm_provider("gemini")
cognee.config.set_llm_model("gemini/gemini-2.5-flash-lite")

# Configure Embeddings to use local Ollama (nomic-embed-text) — avoids paid
# embedding API calls. huggingface_tokenizer must be set explicitly: cognee's
# OllamaEmbeddingEngine forwards it straight into AutoTokenizer.from_pretrained(),
# and the config's default of None crashes with "None is not a local folder".
cognee.config.set_embedding_config({
    "embedding_provider": "ollama",
    "embedding_model": "nomic-embed-text",
    "embedding_dimensions": 768,
    "embedding_endpoint": "http://localhost:11434/api/embed",
    "huggingface_tokenizer": "nomic-ai/nomic-embed-text-v1.5",
})

# The specific datasets/cognitive tracks
DATASETS = [
    "kingdom_history",
    "elder_history",
    "disaster_history",
    "external_world_history",
    "rumor_history",
    "relationship_history"
]

# Retrieval budget. cognee.recall defaults to top_k=15 PER CALL; a single situation/council
# fires 6-7 recall calls and concatenates them, so the old un-capped path produced 30-90 raw
# chunks — a wall of text in the UI and needless tokens in the prompt. We pull a small number
# per call and cap the merged, deduped list at MAX_ECHOES (see dedup_echoes).
DEFAULT_RECALL_TOP_K = 5
MAX_ECHOES = 8

# Human-readable label for each track, shown as a chip on the "Echoes of the Past" and
# council "Recalled from the Tapestry" panels so a memory reads as e.g. "[Rumor] ..." instead
# of anonymous chunk soup.
TRACK_LABELS = {
    "kingdom_history": "Kingdom",
    "elder_history": "Elder",
    "disaster_history": "Disaster",
    "external_world_history": "World",
    "rumor_history": "Rumor",
    "relationship_history": "Relations",
}


def dedup_echoes(echoes: list) -> list:
    """Dedup tagged echoes ({'track','text'}) by text, preserve order, cap at MAX_ECHOES.

    The same underlying chunk is frequently returned by several of the per-situation queries;
    without this the panels show the same sentence 3-4 times. First occurrence wins (keeps the
    track label of whichever query surfaced it first).
    """
    seen = set()
    out = []
    for e in echoes:
        text = (e.get("text") or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(e)
    return out[:MAX_ECHOES]

async def remember_event(event_description: str, dataset_name: str = "kingdom_history"):
    """
    Ingests an event summary into a specific Cognee dataset track.
    """
    if dataset_name not in DATASETS:
        print(f"[Cognee Warning] {dataset_name} is not a standard track. Defaulting to kingdom_history.")
        dataset_name = "kingdom_history"
        
    try:
        await cognee.add(event_description, dataset_name=dataset_name)
        print(f"[Cognee] Staged memory in {dataset_name}: {event_description}")
    except Exception as e:
        print(f"[Cognee Error] Failed to remember event in {dataset_name}: {e}")

async def remember_structured_event(model_instance: BaseModel, dataset_name: str = "kingdom_history"):
    """
    Ingests a structured Pydantic model into a specific Cognee dataset track by converting it to a natural language sentence.
    This allows Cognee's NLP extractors to perfectly identify nodes and edges without getting confused by JSON syntax.
    """
    if dataset_name not in DATASETS:
        print(f"[Cognee Warning] {dataset_name} is not a standard track. Defaulting to kingdom_history.")
        dataset_name = "kingdom_history"
        
    try:
        if hasattr(model_instance, "to_sentence"):
            event_text = model_instance.to_sentence()
        else:
            # Fallback
            event_text = model_instance.model_dump_json()
            
        await cognee.add(event_text, dataset_name=dataset_name)
        print(f"[Cognee] Staged structured memory in {dataset_name}: {event_text}")
    except Exception as e:
        print(f"[Cognee Error] Failed to remember structured event in {dataset_name}: {e}")


# Cognify throttling. cognify runs an expensive LLM entity-extraction pass to compile
# staged memories into the graph. remember_event/add still stages data every turn
# (cheap), but we batch the compile step: it only runs every COGNIFY_EVERY_N triggers,
# or immediately when a caller passes force=True (used after narratively-critical events
# like a council meeting, whose adaptations/grudges future situations query). Datasets
# staged since the last compile accumulate in _pending_datasets so nothing is dropped.
COGNIFY_EVERY_N = 3
_cognify_trigger_count = 0
_pending_datasets = set()


def reset_cognify_state():
    """Clear the cognify throttle counters so a New Game doesn't inherit a half-full batch.

    Called from /reset alongside cognee.forget(everything=True): once the graph is wiped, any
    _pending_datasets carried over from the previous playthrough are stale, and a leftover
    trigger count could make the first real compile fire early (or late).
    """
    global _cognify_trigger_count, _pending_datasets
    _cognify_trigger_count = 0
    _pending_datasets = set()


async def run_cognify(datasets: list = None, force: bool = False):
    """
    Compiles staged memories into the knowledge graph, throttled to save LLM cost.

    Runs cognee.cognify() only every COGNIFY_EVERY_N calls, or immediately if force=True.
    Datasets requested since the last successful compile are batched together, so a
    deferred call never loses data — it's just compiled on the next run.
    """
    global _cognify_trigger_count, _pending_datasets

    _pending_datasets |= set(datasets) if datasets else set(DATASETS)
    _cognify_trigger_count += 1

    if not force and _cognify_trigger_count < COGNIFY_EVERY_N:
        print(f"[Cognee] Cognify deferred ({_cognify_trigger_count}/{COGNIFY_EVERY_N}). "
              f"Pending datasets: {sorted(_pending_datasets)}")
        return

    target_datasets = sorted(_pending_datasets) if _pending_datasets else list(DATASETS)
    try:
        await cognee.cognify(datasets=target_datasets)
        print(f"[Cognee] Cognify completed successfully for: {target_datasets}")
        _pending_datasets = set()  # only clear on success so failures retry next run
    except Exception as e:
        print(f"[Cognee Error] Cognify failed for {target_datasets}: {e}")
        return
    finally:
        _cognify_trigger_count = 0

    # improve() is stage-3 default enrichment (triplet embeddings, local Ollama —
    # no paid LLM call) on top of what cognify() just extracted. Only reachable
    # after a real compile, so it inherits the same throttling as cognify itself.
    for dataset_name in target_datasets:
        try:
            await cognee.improve(dataset=dataset_name)
        except Exception as e:
            print(f"[Cognee Error] Improve failed for {dataset_name}: {e}")

async def visualize_kingdom_graph(output_path: str = None) -> str:
    """
    Renders the full knowledge graph to a self-contained HTML file for inspection.

    NOTE: with ENABLE_BACKEND_ACCESS_CONTROL=false and the local Kuzu graph provider,
    all DATASETS tracks live in one shared physical graph store — dataset= only gates
    authorization, it doesn't partition the graph itself. So there's no such thing as
    a per-track render here; this always shows every track's nodes/edges combined.
    """
    output_path = output_path or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), ".artifacts", "kingdom_graph.html"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    await visualize_graph(output_path, dataset=None)
    return output_path


async def search_memories(query: str, datasets: list = None, top_k: int = DEFAULT_RECALL_TOP_K) -> list:
    """
    Retrieves raw knowledge-graph facts from specific tracks using CHUNKS search.

    COST NOTE: This intentionally passes SearchType.CHUNKS (retrieval-only) instead of
    letting recall() auto-route to GRAPH_COMPLETION. GRAPH_COMPLETION runs an extra LLM
    synthesis pass on every call to write a prose answer — but callers just concatenate
    these into a context string and feed them to another LLM (situation/council generator)
    that does its own synthesis anyway. An explicit CHUNKS query_type bypasses the
    auto-router and returns the same underlying facts with ZERO LLM calls (only a local
    Ollama embedding + graph lookup), eliminating ~9-12 paid Gemini calls per turn with no
    loss of information reaching the generator.
    """
    target_datasets = datasets if datasets else ["kingdom_history"]
    try:
        results = await cognee.recall(
            query_text=query,
            query_type=SearchType.CHUNKS,
            datasets=target_datasets,
            top_k=top_k,
        )
        if not results:
            return []

        memories = []
        for res in results:
            text = _extract_chunk_text(res)
            if text:
                memories.append(text)
        return memories
    except DatasetNotFoundError:
        # Expected on a fresh kingdom (or an early turn): a dataset only gets created by
        # its first cognee.add() call, so tracks like relationship_history/disaster_history
        # legitimately don't exist yet until, say, the first Council meeting fires. "No
        # memories on this track yet" is a normal state, not a failure — stay quiet.
        return []
    except Exception as e:
        print(f"[Cognee Error] Recall failed on {target_datasets}: {e}")
        return []


async def search_memories_tagged(query: str, datasets: list = None, top_k: int = DEFAULT_RECALL_TOP_K) -> list:
    """Like search_memories, but tags each chunk with its source track for UI display.

    Returns a list of {"track": <label>, "text": <chunk>} dicts. The label comes from the
    FIRST dataset queried (a query usually targets one track; when it spans two, the primary
    one leads). Callers accumulate these across several queries then run dedup_echoes().
    """
    texts = await search_memories(query, datasets, top_k=top_k)
    primary = (datasets or ["kingdom_history"])[0]
    label = TRACK_LABELS.get(primary, "Lore")
    return [{"track": label, "text": t} for t in texts]


def _extract_chunk_text(res) -> str:
    """
    Normalizes a single CHUNKS recall result into plain text. recall() with
    query_type=CHUNKS returns ResponseGraphEntry objects (always a populated .text
    field), but this stays defensive against dicts/strings too in case the
    cognee/store version behind it changes shape again.
    """
    if res is None:
        return ""
    if isinstance(res, str):
        return res.strip()
    if isinstance(res, dict):
        for key in ("text", "content", "result", "chunk"):
            val = res.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""
    for attr in ("text", "content", "chunk"):
        val = getattr(res, attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return str(res).strip()

async def find_causative_situation(crisis_description: str) -> dict:
    """
    Queries the graph to trace backward and find the root cause (parent_id) of the current crisis.
    Returns a dict with 'raw_memory' containing the causative situation.
    """
    query = f"Based on the kingdom_history, what specific past situation (with situation_id and title) most directly CAUSED this crisis: '{crisis_description}'? If a direct causal link exists, list the situation_id and title."
    results = await search_memories(query, ["kingdom_history"])
    
    if results:
        return {"raw_memory": ". ".join(results)}
    return None

async def get_elder_stances_on_topic(topic: str) -> str:
    """
    Retrieves exactly which elders historically supported or opposed similar topics.
    """
    query = f"In elder_history, which elders SUPPORTED or OPPOSED concepts related to '{topic}', and what was their rationale?"
    results = await search_memories(query, ["elder_history"])
    return ". ".join(results) if results else "No historical stances on this topic."
