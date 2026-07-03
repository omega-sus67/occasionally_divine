from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from services.db import get_db, init_db, SessionLocal
from models.domain import Kingdom, WorldState, Elder, ChronicleEntry, Adaptation, CouncilMeeting
from api import actions, council
from services.utils import COUNCIL_UNREST_THRESHOLD
import os

app = FastAPI(title="Occasionally Divine API")
app.include_router(actions.router)
app.include_router(council.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Automatically initialize db on startup
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()

@app.get("/world_state")
def get_world_state(db: Session = Depends(get_db)):
    kingdom = db.query(Kingdom).first()
    if not kingdom:
        # Fallback initialization if something went wrong
        init_db(db)
        kingdom = db.query(Kingdom).first()
        if not kingdom:
            raise HTTPException(status_code=500, detail="Failed to initialize Kingdom.")
            
    from models.domain import Rumor
    world_state = kingdom.world_state
    elders = db.query(Elder).filter(Elder.kingdom_id == kingdom.id).all()
    adaptations = db.query(Adaptation).filter(Adaptation.kingdom_id == kingdom.id).all()
    chronicle = db.query(ChronicleEntry).filter(ChronicleEntry.kingdom_id == kingdom.id).order_by(ChronicleEntry.id.desc()).all()
    # Select only the columns we render so this stays robust against older DB schemas
    # (e.g. a saved DB created before rumors.parent_rumor_id existed).
    rumors = db.query(
        Rumor.id, Rumor.content, Rumor.source_elder,
        Rumor.spread, Rumor.created_season, Rumor.created_year,
    ).filter(Rumor.kingdom_id == kingdom.id, Rumor.is_true == -1).order_by(Rumor.id.desc()).all()
    
    # Active council if unrest has crossed the council threshold
    active_council = None
    if kingdom.realm_unrest >= COUNCIL_UNREST_THRESHOLD:
        # Get the latest meeting (which might be in progress or just completed)
        latest_meeting = db.query(CouncilMeeting).filter(CouncilMeeting.kingdom_id == kingdom.id).order_by(CouncilMeeting.id.desc()).first()
        if latest_meeting:
            active_council = latest_meeting.to_dict()
            
    return {
        "kingdom": kingdom.to_dict(),
        "world_state": world_state.to_dict() if world_state else {"tiles": [], "buildings": [], "disasters": []},
        "elders": [e.to_dict() for e in elders],
        "adaptations": [a.to_dict() for a in adaptations],
        "chronicle": [c.to_dict() for c in chronicle],
        "rumors": [
            {
                "id": r.id,
                "content": r.content,
                "source_elder": r.source_elder,
                "spread": r.spread,
                "season": r.created_season,
                "year": r.created_year,
            }
            for r in rumors
        ],
        "active_council": active_council
    }

@app.get("/causality_timeline")
def get_causality_timeline(db: Session = Depends(get_db)):
    from models.domain import Situation
    kingdom = db.query(Kingdom).first()
    if not kingdom:
        raise HTTPException(status_code=404, detail="Kingdom not found")

    situations = db.query(Situation).filter(Situation.kingdom_id == kingdom.id).all()
    
    # Build a lookup dict
    nodes = {
        s.id: {
            "id": s.id,
            "title": s.title,
            "narrative": s.narrative,
            "season": s.season,
            "year": s.year,
            "intervention": s.chosen_intervention,
            "children": []
        }
        for s in situations
    }

    # Build the tree
    tree = []
    for s in situations:
        if s.parent_situation_id and s.parent_situation_id in nodes:
            nodes[s.parent_situation_id]["children"].append(nodes[s.id])
        else:
            tree.append(nodes[s.id])

    return {"timeline": tree}

@app.get("/api/elder_dossier/{kingdom_id}/{elder_name}")
async def get_elder_dossier(kingdom_id: int, elder_name: str, db: Session = Depends(get_db)):
    from models.domain import Elder
    from services.memory import search_memories
    from services.llm_client import generate_chat_completion, parse_json_response

    elder = db.query(Elder).filter(Elder.kingdom_id == kingdom_id, Elder.name == elder_name).first()
    if not elder:
        return {"status": "error", "message": "Elder not found"}

    try:
        history_mem = await search_memories(f"What has {elder_name} supported or opposed in council debates? What are their recent actions?", ["elder_history"])
        relation_mem = await search_memories(f"What grudges or alliances does {elder_name} have?", ["relationship_history"])
    except Exception as e:
        history_mem = []
        relation_mem = []

    prompt = f"""
    You are the Royal Historian, and you're a little tired of these people. Write a dossier for Elder {elder_name} ({elder.role}).
    Mood: {elder.mood} | Belief in Divine: {elder.belief_in_divine}/100

    Records:
    History: {history_mem}
    Relationships: {relation_mem}

    Return ONLY valid JSON in this exact structure:
    {{
        "biography": "String, max 3 sentences. Wry and specific, not dramatic — one vivid detail beats a paragraph of praise. Summarize their career, faith, and one defining flaw or quirk.",
        "relationships": ["String (List of ONE punchy sentence per grudge or alliance. If none, leave empty.)"]
    }}
    """
    
    try:
        raw_response = generate_chat_completion([{"role": "user", "content": prompt}])
        dossier_data = parse_json_response(raw_response)
    except Exception as e:
        print(f"[Warning] Dossier generation failed: {e}")
        dossier_data = {
            "biography": f"{elder_name} is the {elder.role}. Their history is clouded by time.",
            "relationships": []
        }

    return {
        "name": elder.name,
        "role": elder.role,
        "mood": elder.mood,
        "belief": elder.belief_in_divine,
        "biography": dossier_data.get("biography", ""),
        "relationships": dossier_data.get("relationships", [])
    }

@app.get("/memory")
async def get_memory(query: str = "What are the most recent events in the kingdom?"):
    from services.memory import search_memories
    memories = await search_memories(query)
    return {"memories": memories}

from pydantic import BaseModel
class OracleRequest(BaseModel):
    query: str

@app.post("/api/oracle")
async def consult_oracle(req: OracleRequest):
    from services.memory import search_memories
    from services.llm_client import generate_chat_completion
    
    try:
        # Search all possible datasets
        memories = await search_memories(
            req.query, 
            ["kingdom_history", "elder_history", "rumor_history", "relationship_history", "external_world_history"]
        )
        memories_str = "\n".join(memories) if memories else "The Tapestry is silent on this matter."
    except Exception as e:
        memories_str = "The Tapestry is silent on this matter."

    prompt = f"""
    You are the Oracle of the Archives. The Divine (player) asks you: "{req.query}"
    
    Base your answer PURELY on the following historical records retrieved from the Tapestry of Fate:
    {memories_str}
    
    Answer in a mysterious, prophetic, but historically accurate tone. If the records do not contain the answer, admit that the Tapestry is silent on the matter. Do not invent fake history!
    Keep your answer concise (2-4 sentences max). Do not use markdown wrappers.
    """
    
    try:
        raw_response = generate_chat_completion([{"role": "user", "content": prompt}])
        answer = raw_response.strip()
    except Exception as e:
        print(f"[Warning] Oracle generation failed: {e}")
        answer = "The mists of time obscure my vision. I cannot answer right now."

    return {"answer": answer}

@app.post("/reset")
async def reset_game(db: Session = Depends(get_db)):
    from models.domain import Base
    from services.db import engine
    from services.memory import reset_cognify_state

    # Clear the cognee knowledge graph too. With ENABLE_BACKEND_ACCESS_CONTROL=false + local
    # Kuzu, every dataset shares ONE physical graph store, so without this the previous game's
    # chunks stay recallable and leak into the new game's "Echoes of the Past". forget()
    # wipes graph + vectors for all datasets. Wrapped so a graph-clear failure never blocks
    # the SQL reset (the player still gets a fresh game).
    try:
        import cognee
        await cognee.forget(everything=True)
    except Exception as e:
        print(f"[Reset] cognee.forget failed (continuing with SQL reset): {e}")
    reset_cognify_state()

    # Drop all tables and recreate them to reset state
    Base.metadata.drop_all(bind=engine)
    init_db(db)
    return {"status": "success", "message": "Game state reset successfully."}

# Serve the frontend as static files (mounted LAST so API routes above take precedence).
# This makes the frontend's same-origin relative fetches (e.g. /world_state) resolve here.
from fastapi.staticfiles import StaticFiles
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
