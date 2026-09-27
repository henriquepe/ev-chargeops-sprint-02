#!/usr/bin/env python3
"""Executa o fluxo completo via HTTP real e salva evidência sem tokens.
Uso: .venv/bin/python scripts/evidence.py --base http://127.0.0.1:8766 --output docs/evidencias/postgresql
Uma execução fecha o mês de teste; use outro --month ao repetir na mesma base.
"""

import argparse
import html
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base", default="http://127.0.0.1:8766")
parser.add_argument("--month", default="2026-10")
parser.add_argument("--output", default="docs/evidencias/postgresql")
args = parser.parse_args()
client = httpx.Client(base_url=args.base, timeout=30)
report = {
    "executed_at": datetime.now(timezone.utc).isoformat(),
    "base_url": args.base,
    "month": args.month,
    "source": "synthetic_demo",
    "checks": [],
}


def check(name, condition, detail=None):
    assert condition, f"{name}: {detail}"
    report["checks"].append({"name": name, "passed": True, "detail": detail})


def call(method, path, expected=200, **kwargs):
    response = client.request(method, "/api" + path, **kwargs)
    assert response.status_code == expected, (
        f"{method} {path}: {response.status_code} {response.text}"
    )
    return (
        response.json()
        if response.content and "json" in response.headers.get("content-type", "")
        else response.text
    )


health = call("GET", "/health")
report["health"] = health
login = call("POST", "/auth/login", json={"email": "gestor@demo.local", "password": "Demo2026!"})
client.headers["Authorization"] = "Bearer " + login["token"]
report["initial_analytics"] = call("GET", "/analytics?month=2026-09")
report["forecast"] = call("GET", "/forecast?month=2026-09")
report["model"] = call("GET", "/model")
check(
    "Previsão avaliada com separação temporal",
    report["forecast"]["training_end"]
    < report["forecast"]["validation_start"]
    < report["forecast"]["as_of"],
)
call(
    "PUT",
    f"/tariffs/{args.month}",
    json={
        "tariff_kwh": ".95",
        "session_fee": "1.50",
        "idle_fee": ".10",
        "idle_grace_minutes": 15,
        "loss_percent": "2",
        "fixed_fee": "0",
    },
)
results = []
for scenario in ("normal", "interrupted", "promotion", "anomaly", "unidentified", "meter_error"):
    results.append(
        call("POST", "/simulate", expected=201, json={"scenario": scenario, "month": args.month})
    )
check("Simulador registra seis cenários", len(results) == 6)
check(
    "IA retém sessão longa",
    results[3]["anomaly"]["flagged"] and results[3]["eligibility"] == "pending",
    results[3]["anomaly"],
)
check(
    "Identificação e medição retêm cobrança",
    all(s["eligibility"] == "pending" for s in results[4:]),
)
check(
    "Fechamento impede pendências",
    call("POST", f"/billing/{args.month}/close", expected=409)["detail"].startswith("Revise"),
)
for s in results[4:]:
    call(
        "POST",
        f"/sessions/{s['id']}/review",
        expected=422,
        json={"decision": "approve", "reason": "Tentativa inválida de liberar inconsistência"},
    )
    call(
        "POST",
        f"/sessions/{s['id']}/review",
        json={"decision": "exclude", "reason": "Inconsistência confirmada no cenário sintético"},
    )
check("Inconsistências exigem exclusão", True)


# Dois gestores tentam decidir sobre a mesma sessão. Só uma decisão prevalece.
def concurrent_review(_):
    return client.post(
        f"/api/sessions/{results[3]['id']}/review",
        json={"decision": "approve", "reason": "Conferência de duração longa em demonstração"},
    ).status_code


if health["database"] == "postgresql":
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(concurrent_review, range(2)))
    check(
        "Revisões concorrentes não sobrescrevem decisões", sorted(statuses) == [200, 409], statuses
    )
else:
    check("Revisão humana libera anomalia", concurrent_review(0) == 200)
credit = {
    "id": f"evidence-credit-{args.month}",
    "unit_id": "ap101",
    "amount": "5.00",
    "reason": "Crédito didático da validação ponta a ponta",
}
call("POST", f"/billing/{args.month}/credits", expected=201, json=credit)
replay = call("POST", f"/billing/{args.month}/credits", expected=201, json=credit)
check("Crédito idempotente", replay["created"] is False)
original = call("GET", f"/sessions/{results[0]['id']}")["original"]
replay = call("POST", "/sessions", json=original)
check("Sessão idempotente", replay["created"] is False)
report["billing"] = call("POST", f"/billing/{args.month}/close")
check(
    "Rateio exato em centavos",
    report["billing"]["total_cents"] == 2926,
    report["billing"]["total_cents"],
)
check(
    "Mês fechado retorna snapshot idêntico",
    call("POST", f"/billing/{args.month}/close") == report["billing"],
)
call("POST", "/simulate", expected=409, json={"scenario": "normal", "month": args.month})
check("Mês fechado rejeita novas sessões", True)
report["sessions"] = call("GET", f"/sessions?month={args.month}")
report["csv"] = call("GET", f"/billing/{args.month}/csv")
resident = call(
    "POST", "/auth/login", json={"email": "morador101@demo.local", "password": "Demo2026!"}
)
client.headers["Authorization"] = "Bearer " + resident["token"]
private_bill = call("GET", f"/billing/{args.month}")
check(
    "Morador vê somente sua unidade",
    len(private_bill["units"]) == 1 and private_bill["units"][0]["unit_id"] == "ap101",
)
call("GET", "/audit", expected=403)
check("Morador não acessa auditoria administrativa", True)
check(
    "Exportação do morador não contém vizinhos",
    "ap102" not in call("GET", f"/billing/{args.month}/csv"),
)
report["result"] = "PASSED"
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
path.with_suffix(".json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
checks = "".join(
    f"<li><b>✓ {html.escape(c['name'])}</b><p>{html.escape(str(c['detail'] or 'Verificado pela resposta real da API.'))}</p></li>"
    for c in report["checks"]
)
page = f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EV ChargeOps — evidência executada</title><style>body{{font:16px system-ui;max-width:960px;margin:50px auto;padding:24px;background:#f5f8f4;color:#173d36}}h1{{font-size:38px}}small,p{{color:#71866d}}li{{background:white;border:1px solid #dce6d6;border-radius:9px;padding:20px;margin:12px 0;list-style:none}}ul{{padding:0}}pre{{background:#183d34;color:#e2f0de;padding:25px;overflow:auto;border-radius:10px;font-size:12px}}.summary{{padding:25px;background:#c6ebd1;border-radius:10px}}a{{color:#067653}}</style><small>GOODWE + FIAP · ENTERPRISE CHALLENGE 2026</small><h1>Do evento à fatura.<br>Fluxo executado e verificado.</h1><p>Execução HTTP real em {html.escape(report["executed_at"])}. Banco: {health["database"]}. Todos os dados são sintéticos.</p><div class="summary"><b>{len(report["checks"])} verificações aprovadas · fatura de teste R$ 29,26</b><p>Requisições reais ao servidor, com autenticação, persistência e inferência. Código: scripts/evidence.py.</p></div><ul>{checks}</ul><h2>Saída completa</h2><p>Tokens e senhas de sessão não são registrados neste relatório.</p><pre>{html.escape(json.dumps(report, ensure_ascii=False, indent=2))}</pre></html>"""
path.with_suffix(".html").write_text(page, encoding="utf-8")
print(
    json.dumps(
        {
            "result": report["result"],
            "checks": len(report["checks"]),
            "database": health["database"],
            "total_cents": report["billing"]["total_cents"],
            "output": str(path),
        },
        ensure_ascii=False,
    )
)
