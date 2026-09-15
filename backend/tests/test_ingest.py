import pytest

from app.ingest import InvalidAlert, parse_line


def test_parse_alert_with_optional_fields() -> None:
    source_id, payload = parse_line(
        b'{"source_id":"sensor-a","payload":{"timestamp":"2026-08-26T03:08:58.635451+0000",'
        b'"event_type":"alert","flow_id":123,"alert":{"gid":1,"signature_id":2,"rev":1,'
        b'"signature":"test","category":"test","severity":3},"http":{"hostname":"example.test"}}}\n'
    )

    assert source_id == "sensor-a"
    assert payload["flow_id"] == 123
    assert payload["http"]["hostname"] == "example.test"


def test_parse_rejects_missing_rule_identity() -> None:
    with pytest.raises(InvalidAlert):
        parse_line(b'{"source_id":"sensor-a","payload":{"timestamp":"now","event_type":"alert","alert":{}}}')


def test_parse_rejects_non_object() -> None:
    with pytest.raises(InvalidAlert):
        parse_line(b'[]')
