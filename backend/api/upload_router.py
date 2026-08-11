# backend/api/upload_router.py
from fastapi import APIRouter, UploadFile, File, status
from schemas.dataset import UploadResponse
from services.upload_service import UploadService

router = APIRouter(prefix="/api/v1/datasets", tags=["Datasets & Ingestion"])

@router.post(
    "/upload", 
    response_model=UploadResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Upload e conversão de planilha para Parquet"
)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Recebe um arquivo (CSV, XLSX, XLS ou ODS), converte para Parquet
    e retorna o perfil inicial da planilha.
    """
    metadata = await UploadService.process_upload(file)
    return UploadResponse(
        message="Planilha importada e convertida com sucesso!",
        metadata=metadata
    )