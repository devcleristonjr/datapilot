# backend/services/upload_service.py
import os
import uuid
import io
from datetime import datetime
import polars as pl
from fastapi import UploadFile, HTTPException
from schemas.dataset import DatasetMetadata, ColumnInfo

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

class UploadService:
    @staticmethod
    async def process_upload(file: UploadFile) -> DatasetMetadata:
        filename = file.filename or "planilha.csv"
        ext = filename.split(".")[-1].lower()
        
        if ext not in ["csv", "xlsx", "xls", "ods"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato '.{ext}' não suportado. Envie CSV, XLSX, XLS ou ODS."
            )

        dataset_id = str(uuid.uuid4())
        parquet_filename = f"{dataset_id}.parquet"
        parquet_path = os.path.join(STORAGE_DIR, parquet_filename)

        # Leitura dos bytes do arquivo
        content = await file.read()
        file_buffer = io.BytesIO(content)  # Envelopa os bytes em um buffer com suporte a .seek()
        
        try:
            # Polars lendo a partir do buffer em memória
            if ext == "csv":
                df = pl.read_csv(file_buffer)
            elif ext in ["xlsx", "xls", "ods"]:
                df = pl.read_excel(file_buffer)
            else:
                raise ValueError("Formato não suportado")

            # Salva no formato colunar Parquet
            df.write_parquet(parquet_path)

            # Extração de metadados
            columns_info = [
                ColumnInfo(name=col_name, data_type=str(dtype))
                for col_name, dtype in zip(df.columns, df.dtypes)
            ]

            return DatasetMetadata(
                dataset_id=dataset_id,
                filename=filename,
                original_format=ext.upper(),
                total_rows=df.height,
                total_columns=df.width,
                columns=columns_info,
                created_at=datetime.utcnow()
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao processar a planilha: {str(e)}"
            )