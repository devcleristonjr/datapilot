# datapilot/backend/api/export_router.py
from fastapi import APIRouter
from fastapi.responses import FileResponse
from services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["Data & Report Exports"])


@router.get("/csv/{dataset_id}")
def download_csv(dataset_id: str):
    """
    Faz o download do dataset (limpo ou original) formatado como CSV.
    """
    file_path = ExportService.export_csv(dataset_id)
    filename = f"{dataset_id}_clean.csv"
    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename
    )


@router.get("/excel/{dataset_id}")
def download_excel(dataset_id: str):
    """
    Faz o download do dataset (limpo ou original) formatado como planilha Excel (.xlsx).
    """
    file_path = ExportService.export_excel(dataset_id)
    filename = f"{dataset_id}_clean.xlsx"
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )


@router.get("/pdf-report/{dataset_id}")
def download_pdf_report(dataset_id: str):
    """
    Gera e faz o download de um relatório executivo formal em PDF com diagnóstico de qualidade e estatísticas.
    """
    pdf_path = ExportService.generate_pdf_report(dataset_id)
    filename = f"Relatorio_Qualidade_{dataset_id}.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename
    )