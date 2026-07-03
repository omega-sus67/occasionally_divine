from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from services.db import get_db
from council.engine import run_council_meeting, resolve_council_meeting
from models.domain import Kingdom
from services.utils import COUNCIL_UNREST_THRESHOLD

router = APIRouter()

@router.post("/trigger_council")
async def trigger_council(db: Session = Depends(get_db)):
    kingdom = db.query(Kingdom).first()
    if not kingdom:
        raise HTTPException(status_code=404, detail="Kingdom not found.")

    # Only allow trigger once unrest has boiled past the council threshold
    if kingdom.realm_unrest < COUNCIL_UNREST_THRESHOLD:
        raise HTTPException(status_code=400, detail=f"Realm Unrest must be {COUNCIL_UNREST_THRESHOLD} or greater to trigger the Council.")

    result = await run_council_meeting(db, kingdom.id)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))

    return result

@router.post("/resolve_council")
async def resolve_council(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    kingdom = db.query(Kingdom).first()
    if not kingdom:
        raise HTTPException(status_code=404, detail="Kingdom not found.")

    result = await resolve_council_meeting(db, kingdom.id, background_tasks)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result
