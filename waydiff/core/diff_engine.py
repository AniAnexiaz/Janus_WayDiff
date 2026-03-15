import json


# ==========================================================
# INTERNAL NORMALIZATION
# ==========================================================

def _normalize_item(item):
    """
    Convert an item into a stable JSON string for set comparison.

    Handles dicts, lists, and primitive values safely.
    """

    # Dicts and lists can be serialized directly
    if isinstance(item, (dict, list)):
        return json.dumps(item, sort_keys=True)

    # Primitive values are wrapped to avoid ambiguity
    return json.dumps({"value": item}, sort_keys=True)


def _denormalize_item(item_str):
    """
    Convert normalized JSON string back to original structure.
    """

    obj = json.loads(item_str)

    # If wrapped primitive
    if isinstance(obj, dict) and "value" in obj and len(obj) == 1:
        return obj["value"]

    return obj


# ==========================================================
# SECURITY HEADER DIFF
# ==========================================================

def diff_security_headers(old_headers: dict, new_headers: dict):

    old_headers = old_headers or {}
    new_headers = new_headers or {}

    added = {}
    removed = {}
    modified = {}

    old_keys = set(old_headers.keys())
    new_keys = set(new_headers.keys())

    for key in new_keys - old_keys:
        added[key] = new_headers[key]

    for key in old_keys - new_keys:
        removed[key] = old_headers[key]

    for key in old_keys & new_keys:
        if old_headers[key] != new_headers[key]:
            modified[key] = {
                "old": old_headers[key],
                "new": new_headers[key],
            }

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
    }


# ==========================================================
# GENERIC SURFACE DIFF
# ==========================================================

def compute_surface_diff(old_surface, new_surface):

    diff = {}

    all_keys = set(old_surface.keys()) | set(new_surface.keys())

    for key in all_keys:

        # Special handling for headers
        if key == "security_headers":
            diff[key] = diff_security_headers(
                old_surface.get(key, {}),
                new_surface.get(key, {}),
            )
            continue

        old_items = old_surface.get(key, [])
        new_items = new_surface.get(key, [])

        # Normalize items for reliable set comparison
        old_set = {_normalize_item(x) for x in old_items}
        new_set = {_normalize_item(x) for x in new_items}

        added = new_set - old_set
        removed = old_set - new_set

        diff[key] = {
            "added": [_denormalize_item(x) for x in added],
            "removed": [_denormalize_item(x) for x in removed],
        }

    return diff
