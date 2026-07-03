from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text
from sqlalchemy.orm import relationship, declarative_base
import json

Base = declarative_base()

class Kingdom(Base):
    __tablename__ = "kingdoms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Valoria")
    current_year = Column(Integer, default=1)
    current_season = Column(String, default="Spring")
    food = Column(Integer, default=50)
    faith = Column(Integer, default=100)
    population = Column(Integer, default=1000)
    realm_unrest = Column(Integer, default=20)
    divine_influence = Column(Integer, default=50)
    divine_influence_max = Column(Integer, default=100)
    initial_morale = Column(Integer, default=0) # 0 is hope and happiness and 100 mean absolute hopelessness and despair
    current_morale = Column(Integer, default=0) # 0 is hope and happiness and 100 mean absolute hopelessness and despair
    trust_in_ruling_class = Column(Integer, default=50) # 0 is no trust and chances of civil war is conditions are bad and 100 mean absolute trust in ruling class and almost slavery if food and faith are high
    weather = Column(String, default="Clear") # Clear/Rain/Storm/Drought/Fog
    omen_active = Column(String, nullable=True) # "Blood Moon", "Comet", "Eclipse"
    consecutive_disasters = Column(Integer, default=0) # tracks streak for theme escalation
    shrine_level = Column(Integer, default=1) # 1: Wooden Altar, 2: Stone Temple, 3: Cathedral of the Heavens
    game_status = Column(String, default="active") # "active", "victory", "defeat"

    # Relationships
    world_state = relationship("WorldState", uselist=False, back_populates="kingdom")
    elders = relationship("Elder", back_populates="kingdom")
    actions = relationship("PlayerAction", back_populates="kingdom")
    events = relationship("HistoricalEvent", back_populates="kingdom")
    adaptations = relationship("Adaptation", back_populates="kingdom")
    chronicle_entries = relationship("ChronicleEntry", back_populates="kingdom")
    council_meetings = relationship("CouncilMeeting", back_populates="kingdom")
    situations = relationship("Situation", back_populates="kingdom")
    rumors = relationship("Rumor", back_populates="kingdom")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "current_year": self.current_year,
            "current_season": self.current_season,
            "food": self.food,
            "faith": self.faith,
            "population": self.population,
            "realm_unrest": self.realm_unrest,
            "divine_influence": self.divine_influence,
            "divine_influence_max": self.divine_influence_max,
            "current_morale": self.current_morale,
            "trust_in_ruling_class": self.trust_in_ruling_class,
            "weather": self.weather,
            "omen_active": self.omen_active,
            "consecutive_disasters": self.consecutive_disasters,
            "shrine_level": self.shrine_level,
            "game_status": self.game_status,
            "adaptations": [a.to_dict() for a in self.adaptations]
        }


class WorldState(Base):
    __tablename__ = "world_states"

    id = Column(Integer, primary_key=True, index=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    population_mood_json = Column(Text, default='{"hopeful": 40, "fearful": 20, "angry": 10, "devoted": 30}')
    # Store dynamic structure as serialized JSON
    tiles_json = Column(Text, default="[]") 
    buildings_json = Column(Text, default="[]")
    disasters_json = Column(Text, default="[]")

    kingdom = relationship("Kingdom", back_populates="world_state")

    def get_tiles(self):
        return json.loads(self.tiles_json)

    def set_tiles(self, tiles):
        self.tiles_json = json.dumps(tiles)

    def get_buildings(self):
        return json.loads(self.buildings_json)

    def set_buildings(self, buildings):
        self.buildings_json = json.dumps(buildings)

    def get_disasters(self):
        return json.loads(self.disasters_json)

    def set_disasters(self, disasters):
        self.disasters_json = json.dumps(disasters)

    def get_mood(self):
        return json.loads(self.population_mood_json)

    def set_mood(self, mood):
        self.population_mood_json = json.dumps(mood)    
    
    def to_dict(self):
        return {
            "tiles": self.get_tiles(),
            "buildings": self.get_buildings(),
            "disasters": self.get_disasters(),
            "mood": self.get_mood()
        }


class Elder(Base):
    __tablename__ = "elders"

    id = Column(Integer, primary_key=True, index=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    name = Column(String)
    role = Column(String)
    mood = Column(String, default="Neutral")
    personality_key = Column(String)
    stance = Column(String, nullable=True) # their current position: "pro-engineering", "pro-faith"
    memorable_quote = Column(Text, nullable=True) # last notable thing they said (feed back to LLM)
    times_agreed = Column(Integer, default=0) # how often their proposals won
    times_dissented = Column(Integer, default=0) # how often they opposed the majority
    belief_in_divine = Column(Integer, default=50) # 0 is no belief and 100 means absolute belief
    
    kingdom = relationship("Kingdom", back_populates="elders")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "mood": self.mood,
            "personality_key": self.personality_key,
            "stance": self.stance,
            "memorable_quote": self.memorable_quote,
            "belief_in_divine": self.belief_in_divine,
            "times_agreed": self.times_agreed,
            "times_dissented": self.times_dissented
        }


class PlayerAction(Base):
    __tablename__ = "player_actions"

    id = Column(Integer, primary_key=True, index=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    action_type = Column(String)
    cost = Column(Integer)
    season = Column(String)
    year = Column(Integer)
    timestamp = Column(String)

    kingdom = relationship("Kingdom", back_populates="actions")

    def to_dict(self):
        return {
            "id": self.id,
            "action_type": self.action_type,
            "cost": self.cost,
            "season": self.season,
            "year": self.year,
            "timestamp": self.timestamp
        }


class HistoricalEvent(Base):
    __tablename__ = "historical_events"

    id = Column(Integer, primary_key=True, index=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    type = Column(String)
    season = Column(String)
    year = Column(Integer)
    effects_json = Column(Text, default="{}")
    description = Column(Text)
    severity = Column(Integer, default=1)  # how impactful (1-5)
    category = Column(String)  # Nature/Society/Economy/etc.
    theme = Column(String, nullable=True)  # "The River", "The Flame", "The Harvest"
    times_referenced = Column(Integer, default=0)  # how often council/situations mention this
    
    kingdom = relationship("Kingdom", back_populates="events")

    def get_effects(self):
        return json.loads(self.effects_json)

    def set_effects(self, effects):
        self.effects_json = json.dumps(effects)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "season": self.season,
            "year": self.year,
            "effects": self.get_effects(),
            "description": self.description
        }


class Adaptation(Base):
    __tablename__ = "adaptations"

    id = Column(Integer, primary_key=True, index=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    display_name = Column(String)
    trigger_events_json = Column(Text, default="[]")
    gameplay_effect = Column(String)
    constructed_year = Column(Integer)
    status = Column(String, default="proposed")  # proposed → constructing → halted → disputed → completed
    construction_started_season = Column(String, nullable=True)
    construction_started_year = Column(Integer, nullable=True)
    speed = Column(Integer, default=1)   # how many years to complete (1-4)
    resilience_focus = Column(String, nullable=True)  # Situation category this adaptation mechanically dampens (e.g. "Nature")


    kingdom = relationship("Kingdom", back_populates="adaptations")

    def get_trigger_events(self):
        return json.loads(self.trigger_events_json)

    def set_trigger_events(self, trigger_events):
        self.trigger_events_json = json.dumps(trigger_events)

    def to_dict(self):
        return {
            "id": self.id,
            "display_name": self.display_name,
            "trigger_events": self.get_trigger_events(),
            "gameplay_effect": self.gameplay_effect,
            "constructed_year": self.constructed_year,
            "status": self.status,
            "resilience_focus": self.resilience_focus
        }


class ChronicleEntry(Base):
    __tablename__ = "chronicle_entries"

    id = Column(Integer, primary_key=True, index=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    season = Column(String)
    year = Column(Integer)
    summary = Column(Text)
    consequence = Column(Text)
    title = Column(String) # "The Great Flood", "The Year of Empty Granaries"
    narrative = Column(Text) # 3-6 paragraphs, LLM-generated medieval prose
    legacy = Column(Text, nullable=True) # "From that year onward, the kingdom feared the river less."
    historian_tone = Column(String) # tracks if kingdom is hopeful/fearful/resilient

    kingdom = relationship("Kingdom", back_populates="chronicle_entries")

    def to_dict(self):
        return {
            "id": self.id,
            "season": self.season,
            "year": self.year,
            "summary": self.summary,
            "consequence": self.consequence
        }


class CouncilMeeting(Base):
    __tablename__ = "council_meetings"

    id = Column(Integer, primary_key=True, index=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    trigger = Column(String)
    retrieved_memories_json = Column(Text, default="[]")
    discussion_json = Column(Text, default="[]")
    proposal = Column(String)
    adaptation_id = Column(Integer, ForeignKey("adaptations.id"), nullable=True)
    year = Column(Integer)
    season = Column(String)
    dominant_emotion = Column(String, nullable=True)  # "anger", "grief", "hope", "fear", "determination"
    dissent_level = Column(Integer, default=0)         # 0-100, how much the elders disagreed

    kingdom = relationship("Kingdom", back_populates="council_meetings")

    def get_retrieved_memories(self):
        return json.loads(self.retrieved_memories_json)

    def set_retrieved_memories(self, memories):
        self.retrieved_memories_json = json.dumps(memories)

    def get_discussion(self):
        return json.loads(self.discussion_json)

    def set_discussion(self, discussion):
        self.discussion_json = json.dumps(discussion)

    def to_dict(self):
        return {
            "id": self.id,
            "trigger": self.trigger,
            "retrieved_memories": self.get_retrieved_memories(),
            "discussion": self.get_discussion(),
            "proposal": self.proposal,
            "adaptation_id": self.adaptation_id,
            "year": self.year,
            "season": self.season
        }


class Situation(Base):
    __tablename__ = "situations"

    id = Column(Integer, primary_key=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    title = Column(String) # "The River Grows Restless"
    narrative = Column(Text) # The multi-paragraph story the player reads
    category = Column(String) # Nature/Society/Economy/Religion/Infrastructure/Mystery
    severity = Column(Integer, default=1) # 1-5, how urgent
    season = Column(String)
    year = Column(Integer)
    interventions_json = Column(Text) # The 4-6 context-specific actions offered
    chosen_intervention = Column(String, nullable=True)
    parent_situation_id = Column(Integer, ForeignKey("situations.id"), nullable=True)
    retrieved_memories_json = Column(Text, nullable=True)  # Raw Cognee memory strings that informed this situation, for player-facing transparency

    def get_retrieved_memories(self):
        return json.loads(self.retrieved_memories_json) if self.retrieved_memories_json else []

    kingdom = relationship("Kingdom", back_populates="situations")
    parent = relationship("Situation", remote_side=[id])  # chain situations together


class Rumor(Base):
    __tablename__ = "rumors"
    
    id = Column(Integer, primary_key=True)
    kingdom_id = Column(Integer, ForeignKey("kingdoms.id"))
    content = Column(Text)# "Merchants say the western kingdom fell to plague"
    source_elder = Column(String, nullable=True)  # who started it, if known
    is_true = Column(Integer, default=-1)  # -1=unknown, 0=false, 1=true
    spread = Column(Integer, default=0)    # 0-100, how many villagers believe it
    created_season = Column(String)
    created_year = Column(Integer)
    parent_rumor_id = Column(Integer, ForeignKey("rumors.id"), nullable=True)

    kingdom = relationship("Kingdom", back_populates="rumors")
    parent = relationship("Rumor", remote_side=[id])


