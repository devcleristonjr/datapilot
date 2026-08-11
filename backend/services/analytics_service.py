# datapilot/backend/services/analytics_service.py
import os
import math
import polars as pl
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from schemas.analytics import (
    AggregationRequest,
    AggregationResponse,
    DashboardSummaryResponse,
    CategorySummary,
)
from services.profiler_service import ProfilerService

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")


class AnalyticsService:

    @staticmethod
    def _safe_val(val: Any) -> Any:
        """Trata valores NaN e Inf de ponto flutuante para compatibilidade com JSON."""
        if val is None:
            return None
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return None
            return round(val, 2)
        return val

    @classmethod
    def aggregate(cls, req: AggregationRequest) -> AggregationResponse:
        file_path = os.path.join(STORAGE_DIR, f"{req.dataset_id}.parquet")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Dataset não encontrado.")

        df = pl.read_parquet(file_path)

        # Validação de colunas de agrupamento
        for col in req.group_by:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Coluna '{col}' não encontrada no dataset.")

        # Construção das expressões de agregação do Polars
        agg_exprs = []
        for m in req.metrics:
            if m.column not in df.columns and m.function != "count":
                continue

            alias_name = m.alias or f"{m.function}_{m.column}"

            if m.function == "sum":
                agg_exprs.append(pl.col(m.column).sum().alias(alias_name))
            elif m.function == "avg":
                agg_exprs.append(pl.col(m.column).mean().alias(alias_name))
            elif m.function == "min":
                agg_exprs.append(pl.col(m.column).min().alias(alias_name))
            elif m.function == "max":
                agg_exprs.append(pl.col(m.column).max().alias(alias_name))
            elif m.function == "count":
                agg_exprs.append(pl.len().alias(alias_name))
            elif m.function == "n_unique":
                agg_exprs.append(pl.col(m.column).n_unique().alias(alias_name))

        if not agg_exprs:
            # Padrão: contagem de linhas por grupo
            agg_exprs.append(pl.len().alias("count"))

        # Agrupamento e agregação com Polars
        res_df = df.group_by(req.group_by).agg(agg_exprs)

        # Ordenação
        if req.sort_by and req.sort_by in res_df.columns:
            res_df = res_df.sort(req.sort_by, descending=req.sort_descending)

        # Limite Top N
        if req.top_n and req.top_n > 0:
            res_df = res_df.head(req.top_n)

        # Conversão de linhas tratando nulos/NaNs
        raw_dicts = res_df.to_dicts()
        cleaned_dicts = [
            {k: cls._safe_val(v) for k, v in row.items()}
            for row in raw_dicts
        ]

        return AggregationResponse(
            dataset_id=req.dataset_id,
            group_by=req.group_by,
            total_groups=res_df.height,
            data=cleaned_dicts
        )

    @classmethod
    def get_dashboard_summary(cls, dataset_id: str) -> DashboardSummaryResponse:
        file_path = os.path.join(STORAGE_DIR, f"{dataset_id}.parquet")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Dataset não encontrado.")

        df = pl.read_parquet(file_path)
        profile = ProfilerService.generate_profile(dataset_id)
        total_rows = df.height

        def _get_top_categories(col_type: str, limit: int = 5) -> List[CategorySummary]:
            target_cols = [
                cp.name for cp in profile.columns_profile if cp.inferred_type == col_type
            ]
            if not target_cols:
                return []

            target_col = target_cols[0]
            # Identifica se há coluna monetária para somar por categoria
            money_cols = [
                cp.name for cp in profile.columns_profile if cp.inferred_type == "currency"
            ]

            if money_cols:
                m_col = money_cols[0]
                grouped = (
                    df.group_by(target_col)
                    .agg([
                        pl.len().alias("count"),
                        pl.col(m_col).sum().alias("total_value")
                    ])
                    .sort("total_value", descending=True)
                    .head(limit)
                )
            else:
                grouped = (
                    df.group_by(target_col)
                    .agg([pl.len().alias("count")])
                    .sort("count", descending=True)
                    .head(limit)
                )

            res = []
            for row in grouped.to_dicts():
                label = str(row.get(target_col) or "NÃO INFORMADO")
                count = int(row.get("count", 0))
                val = cls._safe_val(row.get("total_value"))
                pct = round((count / total_rows) * 100, 2) if total_rows > 0 else 0.0

                res.append(CategorySummary(
                    label=label,
                    total_value=val,
                    count=count,
                    percentage=pct
                ))
            return res

        return DashboardSummaryResponse(
            dataset_id=dataset_id,
            total_rows=total_rows,
            total_columns=df.width,
            total_monetary_sum=profile.total_monetary_sum,
            top_municipalities=_get_top_categories("municipio"),
            top_organs=_get_top_categories("organ"),
            top_situations=_get_top_categories("situation")
        )