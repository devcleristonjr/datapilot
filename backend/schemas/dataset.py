# backend/schemas/dataset.py
from pydantic import BaseModel
from typing import List
from datetime import datetime

class ColumnInfo(BaseModel):
    name: str
    data_type: str

class DatasetMetadata(BaseModel):
    dataset_id: str
    filename: str
    original_format: str
    total_rows: int
    total_columns: int
    columns: List[ColumnInfo]
    created_at: datetime

class UploadResponse(BaseModel):
    message: str
    metadata: DatasetMetadata