""" File: updates.py
Implements tools and utilities for updating composition files (*.cobf) between different versions. """
from .obfuscation import *
import json

def v0_15_2_to_v_0_15_3(old_dict: dict[str,str]) -> bool:
    old_dict["version"] = "v0.15.3"
    if "transformations" not in old_dict:
        return True
    if not isinstance(old_dict["transformations"], list):
        return True
    for i, t in enumerate(old_dict["transformations"]):
        json_t = json.loads(t)
        if "type" in json_t and json_t["type"] == ControlFlowFlattenUnit.name:
            json_t["randomise_cases"] = False
            json_t["style"] = ControlFlowFlattener.Style.SEQUENTIAL.name
        old_dict["transformations"][i] = json.dumps(json_t)
    return True

UPDATES = {
    "v0.15.2": v0_15_2_to_v_0_15_3
}

def update_version(json_dict: dict[str, str]) -> bool:
    return UPDATES[json_dict["version"]](json_dict)