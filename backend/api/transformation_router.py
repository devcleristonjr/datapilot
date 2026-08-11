# datapilot/backend/api/transformation_router.py
import os
import polars as pl
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from schemas.transformation import TransformationPipelineRequest, TransformationResultResponse
from services.cleaner_service import CleanerService

router = APIRouter(prefix="/api/transform", tags=["Transformations"])

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")


@router.post("/pipeline", response_model=TransformationResultResponse)
def run_transformation_pipeline(request: TransformationPipelineRequest):
    """Executa o pipeline completo de limpeza e transformação no dataset."""
    return CleanerService.apply_pipeline(request)


@router.get("/preview/{dataset_id}")
def preview_dataset(dataset_id: str, limit: int = Query(default=10, le=100)):
    """Retorna uma prévia das primeiras linhas do dataset (original ou limpo)."""
    parquet_path = os.path.join(STORAGE_DIR, f"{dataset_id}.parquet")
    if not os.path.exists(parquet_path):
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    df = pl.read_parquet(parquet_path).head(limit)
    return {
        "dataset_id": dataset_id,
        "columns": df.columns,
        "rows": df.to_dicts()
    }