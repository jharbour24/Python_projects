"""Configuration loader utility."""
import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def get_search_keywords(config: Dict[str, Any]) -> list:
    """Extract search keywords from config."""
    return config.get('keywords', [])


def get_platforms(config: Dict[str, Any]) -> list:
    """Extract platforms from config."""
    return config.get('platforms', [])


def get_movement_lexicon(config: Dict[str, Any]) -> Dict[str, list]:
    """Extract movement language lexicon from config."""
    return config.get('movement_lexicon', {})
