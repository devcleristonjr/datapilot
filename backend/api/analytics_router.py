# datapilot/backend/api/analytics_router.py
from fastapi import APIRouter
from schemas.analytics import AggregationRequest, AggregationResponse, DashboardSummaryResponse
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Aggregations"])


@router.post("/aggregate", response_model=AggregationResponse)
def aggregate_data(request: AggregationRequest):
    """
    Realiza agrupamentos e agregações dinâmicas personalizadas para geração de gráficos.
    Permite somas, médias, contagens e filtros de Top N.
    """
    return AnalyticsService.aggregate(request)


@router.get("/dashboard-summary/{dataset_id}", response_model=DashboardSummaryResponse)
def get_dashboard_summary(dataset_id: str):
    """
    Retorna dados pré-calculados do dataset prontos para alimentar cards e gráficos principais do Dashboard.
    """
    return AnalyticsService.get_dashboard_summary(dataset_id)