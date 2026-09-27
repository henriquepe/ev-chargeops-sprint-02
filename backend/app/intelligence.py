"""Modelos pequenos, explicáveis e treinados exclusivamente com o passado."""

import calendar
import hashlib
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sqlalchemy import select

from .db import DATA_DIR
from .models import ChargingSession

TZ = ZoneInfo("America/Sao_Paulo")
FEATURES = ["energia_kwh", "duracao_min", "potencia_media_kw", "ociosidade_min"]
MODEL_PATH = DATA_DIR / "anomaly-model.json"


def features(s):
    return [
        float(s.energy_kwh),
        float(s.duration_minutes),
        float(s.average_power_kw),
        float(s.idle_minutes),
    ]


def train_anomaly(db, before: date, path=MODEL_PATH):
    rows = [
        s
        for s in db.scalars(select(ChargingSession)).all()
        if s.eligibility == "eligible"
        and not s.quality_issues
        and datetime.fromisoformat(s.ended_at).astimezone(TZ).date() < before
    ]
    if len(rows) < 30:
        raise ValueError("São necessárias ao menos 30 sessões válidas anteriores ao corte.")
    matrix = np.asarray([features(s) for s in rows])
    median = np.median(matrix, axis=0)
    # Piso evita divisão por zero e alarmes por variações irrelevantes.
    scale = np.maximum(1.4826 * np.median(np.abs(matrix - median), axis=0), [2, 20, 1, 10])
    model = dict(
        method="robust-zscore",
        threshold=4.5,
        features=FEATURES,
        median=median.tolist(),
        scale=scale.tolist(),
        training_rows=len(rows),
        trained_before=before.isoformat(),
        training_data_hash=hashlib.sha256(
            json.dumps(sorted((s.id, features(s)) for s in rows)).encode()
        ).hexdigest(),
    )
    model["version"] = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()[:12]
    path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    return model


def score_session(s, path=MODEL_PATH):
    if not path.exists():
        return dict(
            flagged=False,
            status="insufficient_history",
            explanation="Detector ainda sem 30 sessões históricas.",
            version=None,
        )
    model = json.loads(path.read_text(encoding="utf-8"))
    local_day = datetime.fromisoformat(s.started_at).astimezone(TZ).date()
    if local_day < date.fromisoformat(model["trained_before"]):
        return dict(
            flagged=False,
            status="historical_import",
            explanation="Registro anterior ao corte do detector; sem pontuação retrospectiva.",
            version=model["version"],
        )
    x = np.array(features(s))
    z = np.abs(x - model["median"]) / model["scale"]
    # Uma interrupção encurta a sessão; baixo consumo/duração é esperado nesse caso.
    # Excessos e potência/ociosidade atípicas continuam sujeitos à revisão.
    if s.status == "interrupted":
        z[:2] = np.where(x[:2] < model["median"][:2], 0, z[:2])
    reasons = [
        f"{name}: {value:.2f}; referência histórica {center:.2f}; desvio robusto {value_z:.1f}"
        for name, value, center, value_z in zip(FEATURES, x, model["median"], z, strict=True)
        if value_z > model["threshold"]
    ]
    return dict(
        flagged=bool(reasons),
        status="scored",
        score=round(float(z.max()), 2),
        threshold=model["threshold"],
        version=model["version"],
        reasons=reasons,
        explanation="; ".join(reasons)
        if reasons
        else "Sessão compatível com o histórico de referência.",
    )


def design(dates, origin):
    # Tendência linear + dia da semana. Não usa consumo futuro como variável.
    return np.asarray(
        [
            [((d.date() - origin).days / 30)] + [float(d.weekday() == w) for w in range(7)]
            for d in dates
        ]
    )


def forecast(db, month: str, as_of: date):
    month_start = date.fromisoformat(month + "-01")
    month_end = date(
        month_start.year,
        month_start.month,
        calendar.monthrange(month_start.year, month_start.month)[1],
    )
    cutoff = min(as_of, month_end + timedelta(days=1))
    if cutoff < month_start:
        return dict(
            status="insufficient_history",
            explanation="A data de referência antecede o mês solicitado.",
        )
    rows = [
        s
        for s in db.scalars(select(ChargingSession)).all()
        if s.eligibility == "eligible"
        and not s.quality_issues
        and datetime.fromisoformat(s.ended_at).astimezone(TZ).date() < cutoff
    ]
    entries = [
        (
            datetime.fromisoformat(s.started_at).astimezone(TZ).date(),
            float(s.energy_kwh),
        )
        for s in rows
    ]
    if not entries:
        return dict(
            status="insufficient_history",
            explanation="Ainda não há sessões válidas para prever consumo.",
        )
    daily = pd.DataFrame(entries, columns=["day", "kwh"]).groupby("day").kwh.sum()
    dates = pd.date_range(min(daily.index), cutoff - timedelta(days=1), freq="D")
    y = daily.reindex(dates.date, fill_value=0).to_numpy(dtype=float)
    if len(dates) < 35:
        return dict(
            status="insufficient_history",
            explanation="É preciso ter pelo menos 35 dias de observação, incluindo dias sem recarga.",
            days=len(dates),
        )
    origin = dates[0].date()
    x = design(dates, origin)
    split = len(y) - 14
    regressor = Ridge(alpha=1.0).fit(x[:split], y[:split])
    predicted = np.maximum(0, regressor.predict(x[split:]))
    means = {
        w: float(
            np.mean([v for d, v in zip(dates[:split], y[:split], strict=True) if d.weekday() == w])
        )
        for w in range(7)
    }
    baseline = np.array([means[d.weekday()] for d in dates[split:]])
    model_mae = float(mean_absolute_error(y[split:], predicted))
    baseline_mae = float(mean_absolute_error(y[split:], baseline))
    selected = "ridge" if model_mae <= baseline_mae else "weekday_baseline"
    regressor.fit(x, y)
    joblib.dump(regressor, DATA_DIR / "forecast-ridge.joblib")
    future_dates = pd.date_range(cutoff, month_end, freq="D")
    if len(future_dates):
        if selected == "ridge":
            future_values = np.maximum(0, regressor.predict(design(future_dates, origin)))
        else:
            all_means = {
                w: float(np.mean([v for d, v in zip(dates, y, strict=True) if d.weekday() == w]))
                for w in range(7)
            }
            future_values = np.array([all_means[d.weekday()] for d in future_dates])
    else:
        future_values = np.array([])
    observed = sum(v for day, v in entries if month_start <= day < cutoff)
    projected = observed + float(future_values.sum())
    return dict(
        status="ready",
        as_of=cutoff.isoformat(),
        selected_model=selected,
        observed_kwh=round(observed, 2),
        remaining_kwh=round(float(future_values.sum()), 2),
        projected_kwh=round(projected, 2),
        ridge_mae_kwh=round(model_mae, 2),
        baseline_mae_kwh=round(baseline_mae, 2),
        training_days=split,
        validation_days=14,
        training_end=dates[split - 1].date().isoformat(),
        validation_start=dates[split].date().isoformat(),
        validation_end=dates[-1].date().isoformat(),
        forecast_days=len(future_dates),
        data_source="synthetic_demo",
        history=[
            dict(date=d.date().isoformat(), kwh=round(float(v), 2))
            for d, v in zip(dates, y, strict=True)
            if d.date() >= month_start
        ],
        future=[
            dict(date=d.date().isoformat(), kwh=round(float(v), 2))
            for d, v in zip(future_dates, future_values, strict=True)
        ],
        validation=[
            dict(
                date=d.date().isoformat(),
                actual=round(float(a), 2),
                predicted=round(float(p), 2),
                baseline=round(float(b), 2),
            )
            for d, a, p, b in zip(dates[split:], y[split:], predicted, baseline, strict=True)
        ],
        explanation="Projeção de energia validada, não de potência instantânea. Retenções e exclusões não entram na previsão. Comparação temporal de 14 dias; métricas sobre dados sintéticos não comprovam desempenho real.",
    )
