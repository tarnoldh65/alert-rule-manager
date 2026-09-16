from app.autocat import extract_field, find_match


def test_extract_field_reads_nested_path() -> None:
    payload = {"alert": {"signature": "ET SCAN"}, "http": {"hostname": "example.test"}}

    assert extract_field(payload, "alert.signature") == "ET SCAN"
    assert extract_field(payload, "http.hostname") == "example.test"


def test_extract_field_returns_none_for_missing_or_nested_value() -> None:
    payload = {"alert": {"signature": "ET SCAN"}}

    assert extract_field(payload, "alert.missing") is None
    assert extract_field(payload, "missing.path") is None
    assert extract_field(payload, "alert") is None


def test_find_match_returns_first_matching_rule() -> None:
    payload = {"http": {"hostname": "bad.example"}}
    rules = [
        {"id": 1, "category_id": 5, "field_path": "http.hostname", "match_value": "other.example"},
        {"id": 2, "category_id": 6, "field_path": "http.hostname", "match_value": "bad.example"},
    ]

    match = find_match(payload, rules)

    assert match is not None
    assert match["id"] == 2


def test_find_match_returns_none_when_no_rule_matches() -> None:
    assert find_match({"http": {"hostname": "ok.example"}}, [
        {"id": 1, "category_id": 5, "field_path": "http.hostname", "match_value": "bad.example"},
    ]) is None
