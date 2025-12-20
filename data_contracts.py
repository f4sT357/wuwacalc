
from dataclasses import dataclass, field
from typing import List, Dict, Optional, TypedDict

@dataclass
class SubStat:
    stat: str
    value: str  # Kept as string to preserve input format (e.g. "10.8%") initially

@dataclass
class OCRResult:
    substats: list[SubStat]
    log_messages: list[str]
    cost: Optional[str]
    raw_text: str

class DataLoadError(Exception):
    """Raised when data loading fails."""
    pass

@dataclass
class EchoEntry:
    tab_index: int
    cost: Optional[str] = None
    main_stat: Optional[str] = None
    substats: List[SubStat] = field(default_factory=list)

@dataclass
class CharacterProfile:
    internal_name: str
    jp_name: str
    cost_config: str  # e.g. "43311"
    main_stats: Dict[str, str]  # e.g. {"4": "Critical Rate", "3": "Fusion DMG Bonus", "1": "ATK"} 
    weights: Dict[str, float]
    # Note: main_stats keys might need to be specific slots like "4", "3_1", "3_2" etc. if 43311 has multiple 3 costs.
    # The dialog logic saves as: "4", "3_1", "3_2", "1_1", "1_2" roughly.
    # Actually dialog saves as: "4", "3", "3_2" etc based on count.
    # We should ensure this dict handles that structure.

class EchoSaveData(TypedDict):
    """Type definition for the saved JSON structure for a single echo tab."""
    main_stat: str
    substats: List[Dict[str, str]] # list of {"stat": ..., "value": ...}

class AppSaveData(TypedDict):
    """Type definition for the root saved JSON file."""
    config: str
    character: str
    character_jp: Optional[str]
    auto_apply: bool
    score_mode: str
    echoes: Dict[str, EchoSaveData]
