# datapilot/backend/api/ai_router.py
from fastapi import APIRouter
from schemas.ai_diagnostic import AIDiagnosticResponse
from services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["DataPilot AI Diagnostics"])


@router.post("/diagnose/{dataset_id}", response_model=AIDiagnosticResponse)
def diagnose_dataset(dataset_id: str):
    """
    Gera um diagnóstico completo por IA para o dataset:
    - Score de qualidade (0-100)
    - Resumo executivo e falhas estruturais
    - Pipeline recomendado pronto para execução no /api/transform/pipeline
    """
    return AIService.diagnose_dataset(dataset_id)