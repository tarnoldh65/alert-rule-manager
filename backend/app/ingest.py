import json
from collections.abc import Awaitable, Callable


class InvalidAlert(ValueError):
    pass


def validate_alert(payload: dict) -> None:
    required = ("timestamp", "event_type", "alert")
    if any(field not in payload for field in required):
        raise InvalidAlert("alert requires timestamp, event_type, and alert")
    rule_fields = ("gid", "signature_id", "rev", "signature")
    if any(field not in payload["alert"] for field in rule_fields):
        raise InvalidAlert("alert requires complete rule identity")


def parse_line(line: bytes) -> tuple[str, dict]:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise InvalidAlert("line is not valid JSON") from exc
    if not isinstance(message, dict) or not isinstance(message.get("source_id"), str):
        raise InvalidAlert("message requires a source_id")
    payload = message.get("payload")
    if not isinstance(payload, dict):
        raise InvalidAlert("message requires a JSON payload object")
    validate_alert(payload)
    return message["source_id"], payload


async def handle_client(
    reader,
    writer,
    on_alert: Callable[[str, dict], Awaitable[None]],
) -> None:
    source_id = writer.get_extra_info("peername")[0]
    try:
        while line := await reader.readline():
            try:
                configured_source_id, payload = parse_line(line)
                await on_alert(configured_source_id, payload)
                writer.write(b"OK\n")
            except InvalidAlert:
                writer.write(b"INVALID\n")
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()
