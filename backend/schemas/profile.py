# backend/schemas/profile.py
from pydantic import BaseModel
from typing import List, Optional, Any

class ColumnProfile(BaseModel):
    name: str
    raw_type: str
    inferred_type: str  # ex: currency, date, cpf, cnpj, municipio, text, number
    null_count: int
    null_percentage: float
    unique_count: int
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    sum_value: Optional[float] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None

class DatasetProfile(BaseModel):
    dataset_id: str
    total_rows: int
    total_columns: int
    empty_rows_count: int
    empty_columns_count: int
    duplicate_rows_count: int
    total_monetary_sum: float
    unique_municipalities_count: int
    unique_organs_count: int
    unique_situations_count: int
    columns_profile: List[ColumnProfile]