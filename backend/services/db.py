import os
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.domain import Base, Kingdom, WorldState, Elder
import json
from dotenv import load_dotenv

load_dotenv()

# Fallback to local SQLite if PostgreSQL connection fails or isn't specified
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./occasionally_divine.db")

# If using PostgreSQL on port 5433 with peer authentication issue, can set it in env
# e.g., DATABASE_URL=postgresql://postgres:password@localhost:5433/occasionally_divine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(db):
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Check if a kingdom exists
    kingdom = db.query(Kingdom).first()
    if not kingdom:
        # Create default kingdom
        initial_morale_val = random.randint(0, 100)
        kingdom = Kingdom(
            name="Edengrove",
            current_year=1,
            current_season="Spring",
            food=50,
            faith=100,
            population=1000,
            realm_unrest=20,
            divine_influence=50,
            divine_influence_max=100,
            initial_morale=initial_morale_val,
            current_morale=initial_morale_val,
            trust_in_ruling_class=50,
            weather="Clear",
            consecutive_disasters=0
        )
        db.add(kingdom)
        db.flush() # Populate kingdom.id

        # Setup 5x5 tilemap
        # Types: River, Farmland, Forest, Village (holds Houses/Tavern/Blacksmith/Church)
        grid_types = [
            ["River", "Farmland", "Farmland", "Forest", "Forest"],
            ["River", "Farmland", "Farmland", "Village", "Forest"],
            ["River", "Village", "Village", "Village", "Village"],
            ["River", "Farmland", "Farmland", "Village", "Forest"],
            ["River", "Farmland", "Farmland", "Forest", "Forest"],
        ]
        
        tiles = []
        tile_id = 0
        for y in range(5):
            for x in range(5):
                tiles.append({
                    "id": tile_id,
                    "type": grid_types[y][x],
                    "status": "Normal", # Normal, Flooded, Burned
                    "x": x,
                    "y": y
                })
                tile_id += 1

        buildings = [
            {"id": 0, "name": "Chapel", "type": "Church", "status": "Normal", "tile_id": 12},
            {"id": 1, "name": "Tomas' Forge", "type": "Blacksmith", "status": "Normal", "tile_id": 14},
            {"id": 2, "name": "The Rusty Tankard", "type": "Tavern", "status": "Normal", "tile_id": 11},
            {"id": 3, "name": "Rowan's Manor", "type": "House", "status": "Normal", "tile_id": 8},
            {"id": 4, "name": "Peasant Cottages", "type": "House", "status": "Normal", "tile_id": 13},
            {"id": 5, "name": "Grain Store", "type": "House", "status": "Normal", "tile_id": 18}
        ]

        world_state = WorldState(
            kingdom_id=kingdom.id
        )
        world_state.set_tiles(tiles)
        world_state.set_buildings(buildings)
        world_state.set_disasters([])
        # population_mood_json relies on default
        db.add(world_state)

        # Setup Elders
        json_path = os.path.join(os.path.dirname(__file__), "..", "elder_personalities.json")
        try:
            with open(json_path, "r") as f:
                personalities = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load elder personalities: {e}")
            personalities = {}

        elders = []
        elder_roles = [
            ("Rowan", "Elder Rowan"),
            ("Aldric", "Brother Aldric"),
            ("Tomas", "Tomas"),
            ("Martha", "Martha"),
            ("Elric", "Elric")
        ]

        for name, role in elder_roles:
            if name in personalities and len(personalities[name]) > 0:
                flavor = random.choice(personalities[name])
                elders.append(
                    Elder(
                        kingdom_id=kingdom.id,
                        name=name,
                        role=role,
                        personality_key=flavor.get("personality_key", name.lower()),
                        stance=flavor.get("stance", "neutral"),
                        belief_in_divine=flavor.get("belief_in_divine", 50),
                        memorable_quote=flavor.get("memorable_quote", "")
                    )
                )
            else:
                elders.append(Elder(kingdom_id=kingdom.id, name=name, role=role, personality_key=name.lower()))

        db.add_all(elders)
        db.commit()
