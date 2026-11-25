"""Gera 200 eventos fictícios e 20 casos de avaliação reproduzíveis."""

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

SCENARIOS = [
    ("ssh", "Falha de autenticação SSH para usuário admin; acesso negado", 5),
    ("sudo", "Escalação de privilégio via sudo pelo usuário operador; ação permitida", 8),
    ("fim", "Integridade de arquivo: /etc/ssh/sshd_config foi modificado", 7),
    ("malware", "Antivírus detectou arquivo EICAR de teste em C:/Lab/eicar.txt; quarentena", 12),
    ("scan", "Firewall bloqueou varredura de portas TCP 22, 80 e 443", 10),
    ("account", "Conta de laboratório backup_svc criada no host Windows", 6),
    ("sqli", "DVWA: tentativa de SQL injection em /vulnerabilities/sqli/; HTTP 200", 10),
    ("xss", "DVWA: marcador de XSS refletido em /vulnerabilities/xss_r/; HTTP 200", 8),
    ("brute", "DVWA: falha de login repetida em /vulnerabilities/brute/; HTTP 401", 7),
    ("upload", "DVWA: upload de arquivo teste.php em /vulnerabilities/upload/; HTTP 403", 9),
]


def generate(root: Path) -> None:
    output = root / "data" / "samples"
    output.mkdir(parents=True, exist_ok=True)
    wazuh: list[dict[str, Any]] = []
    dvwa: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    epoch = datetime(2026, 11, 1, tzinfo=UTC)
    for group, (kind, description, level) in enumerate(SCENARIOS):
        for n in range(20):
            index = group * 20 + n
            event_id = f"LAB-{kind.upper()}-{n + 1:03d}"
            ip = f"192.0.2.{index + 1}"
            stamp = (epoch + timedelta(minutes=15 * index)).isoformat().replace("+00:00", "Z")
            message = f"{description}. Origem {ip}. Cenário sintético {event_id}."
            if group < 6:
                source = "samples/wazuh_alerts.json"
                host = f"lab-host-{group + 1:02d}"
                wazuh.append(
                    {
                        "id": event_id,
                        "timestamp": stamp,
                        "rule": {
                            "id": str(100001 + group),
                            "level": level,
                            "description": message,
                            "groups": ["lab", kind],
                        },
                        "agent": {"id": str(group + 1), "name": host},
                        "data": {"srcip": ip},
                        "synthetic": True,
                    }
                )
            else:
                source = "samples/dvwa_alerts.csv"
                dvwa.append(
                    {
                        "event_id": event_id,
                        "timestamp": stamp,
                        "host": "dvwa-lab",
                        "src_ip": ip,
                        "level": level,
                        "category": kind,
                        "message": message,
                        "synthetic": "true",
                    }
                )
            if n in (0, 9):
                cases.append(
                    {
                        "id": f"q{len(cases) + 1:02d}",
                        "question": f"O que ocorreu no evento {event_id} de origem {ip}?",
                        "expected_answer": description + f". Origem {ip}.",
                        "expected_sources": [source],
                        "expected_event_ids": [event_id],
                    }
                )
    (output / "wazuh_alerts.json").write_text(
        json.dumps(wazuh, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (output / "dvwa_alerts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dvwa[0]))
        writer.writeheader()
        writer.writerows(dvwa)
    eval_dir = root / "evals"
    eval_dir.mkdir(exist_ok=True)
    (eval_dir / "questions.yaml").write_text(
        yaml.safe_dump({"version": 1, "cases": cases}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print("Gerados 120 eventos Wazuh + 80 DVWA e 20 perguntas.")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1])
