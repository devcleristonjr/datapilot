# backend/api/profile_router.py
from fastapi import APIRouter, status
from schemas.profile import DatasetProfile
from services.profiler_service import ProfilerService

router = APIRouter(prefix="/api/v1/datasets", tags=["Profiling & Analytics"])

@router.get(
    "/{dataset_id}/profile",
    response_model=DatasetProfile,
    status_code=status.HTTP_200_OK,
    summary="Gera e retorna o perfil analítico completo da planilha"
)
def get_dataset_profile(dataset_id: str):
    """
    Retorna estatísticas globais, linhas/colunas vazias, registros duplicados,
    detecção de moeda, CPF, CNPJ, datas e lista de municípios/órgãos.
    """
    return ProfilerService.generate_profile(dataset_id)