import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from data_contracts import HistoryEntry
from utils import get_app_path

class HistoryManager:
    """Manages application history, including saving, loading, and filtering."""
    
    def __init__(self, filename: str = "history.json", max_entries: int = 100):
        self.history_path = os.path.join(get_app_path(), filename)
        self.max_entries = max_entries
        self.logger = logging.getLogger(__name__)
        self._history: List[HistoryEntry] = []
        self.load()

    def load(self) -> None:
        """Loads history from the JSON file."""
        if not os.path.exists(self.history_path):
            self._history = []
            return

        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._history = [
                    HistoryEntry(
                        timestamp=item.get("timestamp", ""),
                        character=item.get("character", ""),
                        cost=item.get("cost", ""),
                        action=item.get("action", ""),
                        result=item.get("result", ""),
                        fingerprint=item.get("fingerprint", ""),
                        details=item.get("details", {})
                    ) for item in data
                ]
            self.logger.info(f"Loaded {len(self._history)} history entries.")
        except Exception as e:
            self.logger.error(f"Failed to load history: {e}")
            self._history = []

    def save(self) -> bool:
        """Saves current history to the JSON file."""
        try:
            data = [
                {
                    "timestamp": h.timestamp,
                    "character": h.character,
                    "cost": h.cost,
                    "action": h.action,
                    "result": h.result,
                    "fingerprint": h.fingerprint,
                    "details": h.details
                } for h in self._history
            ]
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")
            return False

    def add_entry(self, character: str, cost: str, action: str, result: str, fingerprint: str = "", details: Dict[str, Any] = None) -> None:
        """Adds a new history entry and prunes the list if necessary."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = HistoryEntry(
            timestamp=timestamp,
            character=character,
            cost=cost,
            action=action,
            result=result,
            fingerprint=fingerprint,
            details=details or {}
        )
        
        # Insert at the beginning (newest first)
        self._history.insert(0, entry)
        
        # Prune if over limit
        if len(self._history) > self.max_entries:
            self._history = self._history[:self.max_entries]
            
        self.save()

    def find_duplicates(self, fingerprint: str) -> List[int]:
        """Returns a list of indices (IDs) where the fingerprint matches."""
        if not fingerprint:
            return []
        # Return indices of matching entries (0 is newest)
        return [i for i, h in enumerate(self._history) if h.fingerprint == fingerprint]

    def get_entries(self, keyword: str = "", character: str = "", cost: str = "", date_from: str = "", date_to: str = "") -> List[HistoryEntry]:
        """Returns filtered history entries."""
        filtered = self._history
        
        if keyword:
            kw = keyword.lower()
            filtered = [
                h for h in filtered 
                if kw in h.action.lower() or kw in h.result.lower() or kw in h.character.lower()
            ]
            
        if character:
            filtered = [h for h in filtered if h.character == character]
            
        if cost:
            filtered = [h for h in filtered if h.cost == cost]
            
        if date_from:
            filtered = [h for h in filtered if h.timestamp >= date_from]
            
        if date_to:
            to_val = f"{date_to} 23:59:59"
            filtered = [h for h in filtered if h.timestamp <= to_val]
            
        return filtered

    def clear(self) -> None:
        """Clears all history."""
        self._history = []
        self.save()