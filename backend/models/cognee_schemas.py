from pydantic import BaseModel
from typing import List, Optional

class ElderActionMemory(BaseModel):
    """
    Staged to Cognee 'elder_history'. 
    Forces the LLM to extract direct relationships (e.g., Elder -> SUPPORTED/OPPOSED -> Adaptation).
    """
    elder_name: str
    action_type: str  # e.g., "SUPPORTED", "OPPOSED", "PROPOSED", "WARNED_AGAINST"
    target_concept: str # e.g., "Sunken Earth Gardens", "The Player (Divine)"
    rationale: str # The quote or reason they gave
    season: str
    year: int
    
    def to_sentence(self) -> str:
        return f"In Year {self.year}, {self.season}, Elder {self.elder_name} {self.action_type} the concept of {self.target_concept} because they stated: '{self.rationale}'."


class SituationMemory(BaseModel):
    """
    Staged to Cognee 'kingdom_history'.
    Forces the LLM to extract causal links between events.
    """
    situation_id: int
    title: str
    resolution: str
    adaptation_built: Optional[str] = None
    caused_by_situation_id: Optional[int] = None
    caused_by_situation_title: Optional[str] = None
    unrest_change: int
    food_change: int
    season: str
    year: int

    def to_sentence(self) -> str:
        sentence = f"In Year {self.year}, {self.season}, a major event titled '{self.title}' (Situation ID {self.situation_id}) was resolved by '{self.resolution}'."
        if self.adaptation_built:
            sentence += f" This led to the construction of {self.adaptation_built}."
        if self.caused_by_situation_id:
            sentence += f" This situation was directly CAUSED by a previous event: '{self.caused_by_situation_title}' (Situation ID {self.caused_by_situation_id})."
        sentence += f" The resolution shifted unrest by {self.unrest_change} and food by {self.food_change}."
        return sentence

    
class SuspectDivineMemory(BaseModel):
    """
    Staged to Cognee 'rumor_history' or 'elder_history'.
    Used to slowly build up the Elders' realization that the Player (a Divine Entity) is manipulating them.
    """
    elder_name: str
    suspicion_level: str # "Low", "Medium", "High", "Paranoid"
    observation: str # e.g., "The weather changed instantly after the Blight started. This is unnatural."
    season: str
    year: int

    def to_sentence(self) -> str:
        return f"In Year {self.year}, {self.season}, Elder {self.elder_name} showed a {self.suspicion_level} level of suspicion that a divine, unseen power is manipulating the kingdom, observing: '{self.observation}'."


class AdaptationMemory(BaseModel):
    """
    Staged to Cognee 'kingdom_history'.
    Links adaptations to the situations they solve, creating persistent historical learning.
    """
    adaptation_name: str
    solved_situation_id: int
    solved_situation_title: str
    gameplay_effect: str
    resilience_focus: str  # e.g., "famine", "floods", "social unrest"
    season: str
    year: int

    def to_sentence(self) -> str:
        return f"CRITICAL KINGDOM INTELLIGENCE: In Year {self.year}, {self.season}, the kingdom suffered from '{self.solved_situation_title}' (Situation ID {self.solved_situation_id}). To survive, the Council built the adaptation '{self.adaptation_name}'. This adaptation now exists and provides permanent resilience and protection against {self.resilience_focus} and similar calamities."


class InterElderRelationMemory(BaseModel):
    """
    Staged to Cognee 'relationship_history'.
    Tracks grudges, rivalries, and alliances between elders formed during council debates.
    """
    elder_from: str
    elder_to: str
    relation_type: str # "Grudge", "Alliance", "Rivalry"
    reason: str
    intensity: int
    season: str
    year: int

    def to_sentence(self) -> str:
        return f"In Year {self.year}, {self.season}, a {self.relation_type} of intensity {self.intensity}/10 formed: Elder {self.elder_from} feels {self.relation_type} towards Elder {self.elder_to} because {self.reason}."


class RumorMemory(BaseModel):
    """
    Staged to Cognee 'rumor_history'.
    Tracks the evolution of commoner rumors and legends.
    """
    originating_situation: str
    rumor_text: str
    target: str
    parent_rumor_id: int | None
    season: str
    year: int

    def to_sentence(self) -> str:
        evolution_tag = f" (Evolved from an older rumor)" if self.parent_rumor_id else ""
        return f"In Year {self.year}, {self.season}, during the '{self.originating_situation}', a rumor spread targeting {self.target}{evolution_tag}: '{self.rumor_text}'"
