import csv
import hashlib
import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from soc_copilot.models import Event

MAX_FILE_BYTES = 50 * 1024 * 1024


def clean(value: str) -> str:
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    value = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten(value, name))
        else:
            result[name] = value
    return result


def utc_timestamp(value: str) -> str:
    if not value:
        return "unknown"
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp sem fuso horário; inclua Z ou offset como -03:00")
    return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


def normalize(raw: dict[str, Any], source: str, record: int) -> Event:
    data = flatten(raw.get("_source", raw))
    stamp = utc_timestamp(str(data.get("timestamp") or data.get("@timestamp") or ""))
    rule_id = str(data.get("rule.id") or data.get("rule_id") or "")
    kind = "wazuh" if rule_id or "agent.name" in data else "dvwa"
    event_id = str(data.get("event_id") or data.get("id") or "")
    if not event_id:
        event_id = hashlib.sha256(f"{source}:{record}".encode()).hexdigest()[:20]
    description = clean(
        str(
            data.get("rule.description")
            or data.get("description")
            or data.get("message")
            or data.get("full_log")
            or ""
        )
    )
    if not description:
        raise ValueError("registro sem message, description, full_log ou rule.description")
    agent = str(data.get("agent.name") or data.get("host") or "")
    src_ip = str(data.get("data.srcip") or data.get("src_ip") or data.get("srcip") or "")
    level = int(data.get("rule.level") or data.get("level") or 0)
    if not 0 <= level <= 16:
        raise ValueError("nível fora do intervalo 0..16")
    # A descrição vem primeiro; campos extras preservam os detalhes para investigação.
    details = " | ".join(
        f"{key}={clean(json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value))}"
        for key, value in sorted(data.items())
        if value is not None and value != ""
    )
    return Event(
        event_id=event_id,
        source=source,
        record=record,
        timestamp=stamp,
        kind=kind,
        rule_id=rule_id,
        level=level,
        agent=agent,
        src_ip=src_ip,
        text=f"{description} | {details}",
    )


def parse_file(path: Path, root: Path) -> list[Event]:
    path, root = path.resolve(), root.resolve()
    if not path.is_relative_to(root):
        raise ValueError("arquivo fora de DATA_DIR")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("arquivo excede 50 MiB; divida a exportação")
    source = path.relative_to(root).as_posix()
    content = path.read_text(encoding="utf-8-sig")
    rows: list[Any]
    if path.suffix.lower() == ".csv":
        if not content.strip():
            return []
        try:
            dialect = csv.Sniffer().sniff(content[:8192], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.DictReader(io.StringIO(content), dialect=dialect))
    elif path.suffix.lower() in {".json", ".jsonl", ".ndjson"}:
        if not content.strip():
            return []
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in content.splitlines() if line.strip()]
        else:
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict) and isinstance(payload.get("hits"), dict):
                rows = payload["hits"]["hits"]
            elif isinstance(payload, dict):
                rows = [payload]
            else:
                raise ValueError("JSON deve conter objeto, lista ou hits.hits")
    else:
        raise ValueError("formato aceito: JSON, JSONL, NDJSON ou CSV")
    events = []
    for record, raw in enumerate(rows, 1):
        try:
            if not isinstance(raw, dict):
                raise ValueError("registro não é objeto")
            events.append(normalize(raw, source, record))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"{source}: registro {record} inválido ({exc})") from exc
    return events
