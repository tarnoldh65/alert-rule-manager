def extract_field(payload: dict, field_path: str) -> str | None:
    value: object = payload
    for part in field_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return None if isinstance(value, (dict, list)) else str(value)


def find_match(payload: dict, rules: list[dict]) -> dict | None:
    for rule in rules:
        if extract_field(payload, rule["field_path"]) == rule["match_value"]:
            return rule
    return None
