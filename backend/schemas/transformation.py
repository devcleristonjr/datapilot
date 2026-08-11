# datapilot/backend/schemas/transformation.py
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field


class FillNullsOp(BaseModel):
    column: str
    strategy: Literal["value", "mean", "median", "drop_rows", "ffill", "bfill"]
    fill_value: Optional[Union[str, int, float]] = None


class StandardizeTextOp(BaseModel):
    column: str
    action: Literal["uppercase", "lowercase", "trim", "remove_accents", "titlecase"]


class StandardizeIdentifierOp(BaseModel):
    column: str
    id_type: Literal["cpf", "cnpj", "currency"]


class CastColumnOp(BaseModel):
    column: str
    target_type: Literal["Utf8", "Int64", "Float64", "Date", "Boolean"]


class RenameColumnOp(BaseModel):
    old_name: str
    new_name: str


class TransformationPipelineRequest(BaseModel):
    dataset_id: str
    drop_columns: Optional[List[str]] = Field(default_factory=list)
    remove_duplicates: bool = False
    duplicate_subset: Optional[List[str]] = None
    drop_empty_rows: bool = False
    fill_nulls: Optional[List[FillNullsOp]] = Field(default_factory=list)
    text_standardizations: Optional[List[StandardizeTextOp]] = Field(default_factory=list)
    identifier_standardizations: Optional[List[StandardizeIdentifierOp]] = Field(default_factory=list)
    type_casts: Optional[List[CastColumnOp]] = Field(default_factory=list)
    rename_columns: Optional[List[RenameColumnOp]] = Field(default_factory=list)
    overwrite_original: bool = False


class TransformationResultResponse(BaseModel):
    dataset_id: str
    clean_dataset_id: str
    original_rows: int
    cleaned_rows: int
    removed_rows: int
    original_cols: int
    cleaned_cols: int
    applied_steps: List[str]