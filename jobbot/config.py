from __future__ import annotations
from pathlib import Path
import yaml

def load(path: str | Path = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as stream:
        return yaml.safe_load(stream)
