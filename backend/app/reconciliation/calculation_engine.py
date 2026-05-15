"""
Rhadix Reconciliation Engine — Calculation Engine
Laadt brondata, past filters toe en berekent de verwachte indicatorwaarde.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .rule_engine import AggregationConfig, FilterCondition, IndicatorRule


@dataclass
class CalcResult:
    indicator_id: str
    expected_value: float | int | None
    record_count: int
    included_records: list[dict]
    excluded_records: list[dict]
    metadata: dict = field(default_factory=dict)


class DataLoader:
    @staticmethod
    def load(source, **read_kwargs) -> pd.DataFrame:
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.suffix in {".xlsx", ".xls"}:
                return pd.read_excel(path, **read_kwargs)
            return pd.read_csv(path, **read_kwargs)
        if isinstance(source, bytes):
            source = io.BytesIO(source)
        try:
            source.seek(0)
            return pd.read_csv(source, **read_kwargs)
        except Exception:
            source.seek(0)
            return pd.read_excel(source, **read_kwargs)


def _apply_filter(df: pd.DataFrame, condition: FilterCondition) -> pd.Series:
    col = df[condition.field]
    op = condition.operator
    val = condition.value
    if op == "eq":      return col == val
    if op == "ne":      return col != val
    if op == "gt":      return col > val
    if op == "gte":     return col >= val
    if op == "lt":      return col < val
    if op == "lte":     return col <= val
    if op == "in":      return col.isin(val)
    if op == "not_in":  return ~col.isin(val)
    if op == "notnull": return col.notna()
    if op == "isnull":  return col.isna()
    raise ValueError(f"Onbekende operator: {op}")


class CalculationEngine:
    def __init__(self, data_dir=None) -> None:
        self.data_dir = Path(data_dir) if data_dir else None

    def calculate(self, rule: IndicatorRule, source=None) -> CalcResult:
        df = self._load_data(rule, source)
        df_included, df_excluded = self._apply_filters(df, rule)
        expected_value = self._aggregate(df_included, rule.aggregation)
        return CalcResult(
            indicator_id=rule.indicator_id,
            expected_value=expected_value,
            record_count=len(df_included),
            included_records=df_included.to_dict(orient="records"),
            excluded_records=df_excluded.to_dict(orient="records"),
            metadata={"total_rows": len(df), "peildatum": rule.peildatum, "source_dataset": rule.source_dataset},
        )

    def _load_data(self, rule, source):
        if source is None:
            if self.data_dir is None:
                raise ValueError("Geen data_dir ingesteld en geen source opgegeven.")
            source = self.data_dir / rule.source_dataset
        return DataLoader.load(source)

    def _apply_filters(self, df, rule):
        mask = pd.Series([True] * len(df), index=df.index)
        for condition in rule.filters:
            if condition.field not in df.columns:
                continue
            mask &= _apply_filter(df, condition)
        if rule.peildatum and rule.peildatum_field and rule.peildatum_field in df.columns:
            df[rule.peildatum_field] = pd.to_datetime(df[rule.peildatum_field], errors="coerce")
            cutoff = pd.Timestamp(rule.peildatum)
            mask &= (df[rule.peildatum_field].isna()) | (df[rule.peildatum_field] >= cutoff)
        return df[mask].copy(), df[~mask].copy()

    @staticmethod
    def _aggregate(df, agg: AggregationConfig):
        if df.empty:
            return 0
        fn, col = agg.function, agg.field
        if fn == "count":   return int(len(df) if col is None else df[col].count())
        if col is None:     raise ValueError(f"Aggregatiefunctie '{fn}' vereist een 'field'.")
        if fn == "sum":     return float(df[col].sum())
        if fn == "mean":    v = df[col].mean();    return round(float(v), 4) if not pd.isna(v) else None
        if fn == "median":  v = df[col].median();  return round(float(v), 4) if not pd.isna(v) else None
        if fn == "nunique": return int(df[col].nunique())
        raise ValueError(f"Onbekende aggregatiefunctie: {fn}")
