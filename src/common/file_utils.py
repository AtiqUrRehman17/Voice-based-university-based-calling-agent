"""
file_utils.py - Reusable filesystem operations.
"""
import json
from pathlib import Path
from typing import Any, List, Dict
from src.common.logger import logger

def ensure_dir(path: Path) -> Path:
    """Ensures a directory exists, creating parents if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_json(data: Any, filepath: Path, indent: int = 2) -> bool:
    """Saves structured data to a JSON file."""
    try:
        ensure_dir(filepath.parent)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        logger.info(f"Saved JSON: {filepath} ({len(data) if isinstance(data, list) else 1} items)")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}")
        return False

def load_json(filepath: Path) -> List[Dict[str, Any]]:
    """Loads a list of JSON records from a file."""
    try:
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
    except Exception as e:
        logger.error(f"Failed to read JSON from {filepath}: {e}")
        return []
