# datapilot/backend/schemas/analytics.py
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class MetricSpec(BaseModel):
    column: str
    function: Literal["sum", "avg", "count", "min", "max", "n_unique"]
    alias: Optional[str] = None


class AggregationRequest(BaseModel):
    dataset_id: str
    group_by: List[str] = Field(..., description="Colunas para agrupamento (ex: ['municipio', 'secretaria'])")
    metrics: List[MetricSpec] = Field(..., description="Lista de agregações a realizar")
    top_n: Optional[int] = Field(default=None, description="Limitar aos N principais resultados")
    sort_by: Optional[str] = Field(default=None, description="Coluna para ordenação dos resultados")
    sort_descending: bool = True


class AggregationResponse(BaseModel):
    dataset_id: str
    group_by: List[str]
    total_groups: int
    data: List[Dict[str, Any]]


class CategorySummary(BaseModel):
    label: str
    total_value: Optional[float] = None
    count: int
    percentage: float


class DashboardSummaryResponse(BaseModel):
    dataset_id: str
    total_rows: int
    total_columns: int
    total_monetary_sum: float
    top_municipalities: List[CategorySummary]
    top_organs: List[CategorySummary]
    top_situations: List[CategorySummary]