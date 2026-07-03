from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.db import get_db
from services.action_handler import execute_intervention
from services.situation_engine import generate_situation
from data.minor_cards import draw_minor_cards
from models.domain import Kingdom
import json

router = APIRouter()

class InterventionRequest(BaseModel):
    situation_id: int
    intervention_index: int
    # Optional minor-card choices for this turn, keyed by param name:
    #   { "food": {"card_id": "good_catch", "option_index": 0}, ... }
    minor_choices: dict | None = None

@router.post("/generate_situation")
async def api_generate_situation(db: Session = Depends(get_db)):
    kingdom = db.query(Kingdom).first()
    if not kingdom:
        raise HTTPException(status_code=404, detail="Kingdom not found.")

    situation = await generate_situation(db, kingdom.id)

    # Resolve the parent's title so the UI can render a "Consequence of: X" badge
    parent_title = None
    if situation.parent_situation_id:
        from models.domain import Situation
        parent = db.query(Situation).filter(Situation.id == situation.parent_situation_id).first()
        parent_title = parent.title if parent else None

    return {
        "status": "success",
        "situation": {
            "id": situation.id,
            "title": situation.title,
            "narrative": situation.narrative,
            "category": situation.category,
            "severity": situation.severity,
            "interventions": json.loads(situation.interventions_json),
            "parent_situation_id": situation.parent_situation_id,
            "parent_situation_title": parent_title,
            "retrieved_memories": situation.get_retrieved_memories(),
        },
        # 2-3 randomly drawn per-parameter minor cards for this turn (no LLM cost).
        "minor_cards": draw_minor_cards(),
    }

@router.post("/execute_intervention")
async def api_execute_intervention(req: InterventionRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    kingdom = db.query(Kingdom).first()
    if not kingdom:
        raise HTTPException(status_code=404, detail="Kingdom not found.")

    result = await execute_intervention(db, kingdom.id, req.situation_id, req.intervention_index, background_tasks, req.minor_choices)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result
