from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from pydantic import BaseModel, Field

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class ForecastPoint(BaseModel):
    date: str
    value: float
    lower_bound: float | None = None
    upper_bound: float | None = None


class ForecastResult(BaseModel):
    entity_type: str
    entity_id: str
    entity_name: str
    metric: str
    history: list[ForecastPoint] = Field(default_factory=list)
    forecast: list[ForecastPoint] = Field(default_factory=list)
    mae: float | None = None
    mape: float | None = None
    confidence: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


def _linear_regression_forecast(
    values: list[float],
    periods: int = 12,
    confidence: float = 0.95,
) -> tuple[list[float], list[float], list[float]]:
    n = len(values)
    if n < 2:
        mean = sum(values) / max(n, 1) if n > 0 else 0
        return [mean] * periods, [mean * 0.8] * periods, [mean * 1.2] * periods

    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(values) / n

    num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values, strict=False))
    den = sum((xi - x_mean) ** 2 for xi in x)

    slope = num / den if den != 0 else 0
    intercept = y_mean - slope * x_mean

    residuals = [yi - (slope * xi + intercept) for xi, yi in zip(x, values, strict=False)]
    mse = sum(r ** 2 for r in residuals) / max(n, 1)
    std_err = math.sqrt(mse) if mse > 0 else 0

    z = 1.96 if confidence >= 0.95 else 1.645

    forecast_values: list[float] = []
    lower_values: list[float] = []
    upper_values: list[float] = []

    for i in range(periods):
        xi = n + i
        pred = slope * xi + intercept

        pred_std_err = std_err * math.sqrt(1 + 1 / n + ((xi - x_mean) ** 2) / max(den, 1))
        margin = z * pred_std_err if pred_std_err > 0 else abs(pred) * 0.2

        forecast_values.append(max(0, pred))
        lower_values.append(max(0, pred - margin))
        upper_values.append(pred + margin)

    return forecast_values, lower_values, upper_values


def _calculate_mae(actual: list[float], predicted: list[float]) -> float:
    n = min(len(actual), len(predicted))
    if n == 0:
        return 0.0
    return sum(abs(a - p) for a, p in zip(actual[:n], predicted[:n], strict=False)) / n


def _calculate_mape(actual: list[float], predicted: list[float]) -> float:
    n = min(len(actual), len(predicted))
    if n == 0:
        return 0.0
    non_zero = [(a, p) for a, p in zip(actual[:n], predicted[:n], strict=False) if a != 0]
    if not non_zero:
        return 0.0
    return sum(abs(a - p) / abs(a) for a, p in non_zero) / len(non_zero) * 100


class ForecastingService:
    async def forecast_revenue(self, tenant_id: UUID, periods: int = 12) -> ForecastResult:
        async with get_tenant_session(tenant_id) as session:
            rows = (await session.execute(
                text("SELECT metric_date, mrr FROM revenue_metrics WHERE tenant_id = :tid ORDER BY metric_date ASC"),
                {"tid": tenant_id},
            )).fetchall()

        values = [float(r[1]) for r in rows if r[1] is not None]
        if not values:
            return ForecastResult(
                entity_type="tenant", entity_id=str(tenant_id),
                entity_name="Revenue", metric="mrr",
                history=[], forecast=[], confidence=0.0,
                error_message="Insufficient historical data for forecasting",
            )

        forecast_vals, lower_vals, upper_vals = _linear_regression_forecast(values, periods)

        history = [ForecastPoint(date=str(r[0]), value=float(r[1])) for r in rows if r[1] is not None]
        last_date = datetime.utcnow()
        forecast = [
            ForecastPoint(
                date=(last_date + timedelta(days=30 * (i + 1))).strftime("%Y-%m-%d"),
                value=round(forecast_vals[i], 2),
                lower_bound=round(lower_vals[i], 2),
                upper_bound=round(upper_vals[i], 2),
            )
            for i in range(periods)
        ]

        mae = _calculate_mae(values[-min(len(values), 6):], forecast_vals[:min(periods, 6)])
        mape = _calculate_mape(values[-min(len(values), 6):], forecast_vals[:min(periods, 6)])

        return ForecastResult(
            entity_type="tenant", entity_id=str(tenant_id),
            entity_name="Revenue", metric="mrr",
            history=history, forecast=forecast,
            mae=round(mae, 2), mape=round(mape, 2) if mape else None,
            confidence=0.85,
        )

    async def forecast_campaign(self, tenant_id: UUID, campaign_id: UUID, periods: int = 12) -> ForecastResult:
        async with get_tenant_session(tenant_id) as session:
            entity_name = (await session.execute(
                text("SELECT name FROM backlink_campaigns WHERE id = :cid AND tenant_id = :tid"),
                {"cid": campaign_id, "tid": tenant_id},
            )).scalar_one_or_none() or str(campaign_id)

            rows = (await session.execute(
                text("SELECT captured_at, health_score FROM campaign_health_snapshots WHERE tenant_id = :tid AND campaign_id = :cid ORDER BY captured_at ASC"),
                {"tid": tenant_id, "cid": campaign_id},
            )).fetchall()

        values = [float(r[1]) for r in rows if r[1] is not None]
        if not values:
            return ForecastResult(
                entity_type="campaign", entity_id=str(campaign_id),
                entity_name=str(entity_name), metric="health_score",
                history=[], forecast=[], confidence=0.0,
                error_message="Insufficient historical data for forecasting",
            )

        forecast_vals, lower_vals, upper_vals = _linear_regression_forecast(values, periods)

        return ForecastResult(
            entity_type="campaign", entity_id=str(campaign_id),
            entity_name=str(entity_name), metric="health_score",
            history=[ForecastPoint(date=str(r[0]), value=float(r[1])) for r in rows if r[1] is not None],
            forecast=[
                ForecastPoint(
                    date=(datetime.utcnow() + timedelta(days=30 * (i + 1))).strftime("%Y-%m-%d"),
                    value=round(forecast_vals[i], 2),
                    lower_bound=round(max(0, lower_vals[i]), 2),
                    upper_bound=round(min(100, upper_vals[i]), 2),
                )
                for i in range(periods)
            ],
            mae=round(_calculate_mae(values[-min(len(values), 6):], forecast_vals[:min(periods, 6)]), 2),
            confidence=0.80,
        )

    async def forecast_customer(self, tenant_id: UUID, customer_id: UUID, periods: int = 12) -> ForecastResult:
        async with get_tenant_session(tenant_id) as session:
            entity_name = (await session.execute(
                text("SELECT name FROM clients WHERE id = :cid AND tenant_id = :tid"),
                {"cid": customer_id, "tid": tenant_id},
            )).scalar_one_or_none() or str(customer_id)

            rows = (await session.execute(
                text("SELECT calculated_at, health_score FROM customer_health_scores WHERE tenant_id = :tid AND client_id = :cid ORDER BY calculated_at ASC"),
                {"tid": tenant_id, "cid": customer_id},
            )).fetchall()

        values = [float(r[1]) for r in rows if r[1] is not None]
        if not values:
            return ForecastResult(
                entity_type="customer", entity_id=str(customer_id),
                entity_name=str(entity_name), metric="health_score",
                history=[], forecast=[], confidence=0.0,
                error_message="Insufficient historical data for forecasting",
            )

        forecast_vals, lower_vals, upper_vals = _linear_regression_forecast(values, periods)

        return ForecastResult(
            entity_type="customer", entity_id=str(customer_id),
            entity_name=str(entity_name), metric="health_score",
            history=[ForecastPoint(date=str(r[0]), value=float(r[1])) for r in rows if r[1] is not None],
            forecast=[
                ForecastPoint(
                    date=(datetime.utcnow() + timedelta(days=30 * (i + 1))).strftime("%Y-%m-%d"),
                    value=round(forecast_vals[i], 2),
                    lower_bound=round(max(0, lower_vals[i]), 2), upper_bound=round(min(100, upper_vals[i]), 2),
                )
                for i in range(periods)
            ],
            mae=round(_calculate_mae(values[-min(len(values), 6):], forecast_vals[:min(periods, 6)]), 2),
            confidence=0.80,
        )

    async def backtest_revenue(self, tenant_id: UUID) -> dict[str, Any]:
        async with get_tenant_session(tenant_id) as session:
            rows = (await session.execute(
                text("SELECT metric_date, mrr FROM revenue_metrics WHERE tenant_id = :tid ORDER BY metric_date ASC"),
                {"tid": tenant_id},
            )).fetchall()

        all_values = [float(r[1]) for r in rows if r[1] is not None]
        if not all_values:
            return {"mae": 0, "mape": 0, "train_size": 0, "test_size": 0, "error": "Insufficient historical data for backtesting"}

        split = max(len(all_values) // 2, 3)
        train = all_values[:split]
        test = all_values[split:]

        if not test:
            return {"mae": 0, "mape": 0, "train_size": len(train), "test_size": 0}

        preds, _, _ = _linear_regression_forecast(train, len(test))
        return {
            "mae": round(_calculate_mae(test, preds), 2),
            "mape": round(_calculate_mape(test, preds), 2) if _calculate_mape(test, preds) else None,
            "train_size": len(train), "test_size": len(test),
            "forecast_values": [round(v, 2) for v in preds],
            "actual_values": [round(v, 2) for v in test],
        }


forecasting_service = ForecastingService()
