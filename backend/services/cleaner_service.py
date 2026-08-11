# datapilot/backend/services/cleaner_service.py
import os
import re
import unicodedata
import polars as pl
from typing import List, Tuple
from fastapi import HTTPException
from schemas.transformation import TransformationPipelineRequest, TransformationResultResponse

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")


class CleanerService:

    @staticmethod
    def _remove_accents(text: str) -> str:
        if not text:
            return ""
        nfkd = unicodedata.normalize('NFKD', str(text))
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    @staticmethod
    def _clean_currency_expr(col_name: str) -> pl.Expr:
        return (
            pl.col(col_name)
            .cast(pl.Utf8, strict=False)
            .str.replace_all(r"[R$\s]", "")
            .str.replace_all(r"\.", "")
            .str.replace(",", ".")
            .cast(pl.Float64, strict=False)
        )

    @classmethod
    def apply_pipeline(cls, req: TransformationPipelineRequest) -> TransformationResultResponse:
        input_path = os.path.join(STORAGE_DIR, f"{req.dataset_id}.parquet")
        if not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail="Dataset não encontrado.")

        df = pl.read_parquet(input_path)
        original_rows = df.height
        original_cols = df.width
        applied_steps: List[str] = []

        # 1. Remover colunas desnecessárias
        if req.drop_columns:
            valid_drops = [c for c in req.drop_columns if c in df.columns]
            if valid_drops:
                df = df.drop(valid_drops)
                applied_steps.append(f"Removidas {len(valid_drops)} colunas: {', '.join(valid_drops)}")

        # 2. Remover linhas completamente vazias
        if req.drop_empty_rows:
            all_cols = df.columns
            # Considera vazia se for null ou string em branco
            empty_cond = pl.all_horizontal([
                pl.col(c).is_null() | (pl.col(c).cast(pl.Utf8, strict=False).str.strip_chars() == "")
                for c in all_cols
            ])
            df = df.filter(~empty_cond)
            applied_steps.append("Removidas linhas completamente vazias")

        # 3. Remover duplicatas
        if req.remove_duplicates:
            subset = req.duplicate_subset if req.duplicate_subset else None
            before_dup = df.height
            df = df.unique(subset=subset, keep="first")
            dups_removed = before_dup - df.height
            applied_steps.append(f"Removidas {dups_removed} linhas duplicadas")

        # 4. Padronização de Texto
        if req.text_standardizations:
            exprs = []
            for op in req.text_standardizations:
                if op.column not in df.columns:
                    continue
                c_expr = pl.col(op.column).cast(pl.Utf8, strict=False)
                if op.action == "trim":
                    c_expr = c_expr.str.strip_chars()
                elif op.action == "uppercase":
                    c_expr = c_expr.str.to_uppercase().str.strip_chars()
                elif op.action == "lowercase":
                    c_expr = c_expr.str.to_lowercase().str.strip_chars()
                elif op.action == "titlecase":
                    c_expr = c_expr.str.to_titlecase().str.strip_chars()
                elif op.action == "remove_accents":
                    # Mapeia via Python para tratamento Unicode preciso
                    col_list = df[op.column].to_list()
                    cleaned_list = [cls._remove_accents(x) if x is not None else None for x in col_list]
                    df = df.with_columns(pl.Series(op.column, cleaned_list))
                    applied_steps.append(f"Acentos removidos da coluna '{op.column}'")
                    continue
                exprs.append(c_expr.alias(op.column))

            if exprs:
                df = df.with_columns(exprs)
                applied_steps.append(f"Padronizações de texto aplicadas em {len(exprs)} colunas")

        # 5. Formatação de Identificadores e Valores (CPF, CNPJ, Moeda)
        if req.identifier_standardizations:
            for op in req.identifier_standardizations:
                if op.column not in df.columns:
                    continue
                if op.id_type == "currency":
                    df = df.with_columns(cls._clean_currency_expr(op.column).alias(op.column))
                    applied_steps.append(f"Coluna '{op.column}' convertida para valor numérico (Float64)")
                elif op.id_type in ["cpf", "cnpj"]:
                    # Remove caracteres não numéricos
                    digits_expr = (
                        pl.col(op.column)
                        .cast(pl.Utf8, strict=False)
                        .str.replace_all(r"\D", "")
                    )
                    df = df.with_columns(digits_expr.alias(op.column))
                    applied_steps.append(f"Apenas dígitos mantidos na coluna '{op.column}' ({op.id_type.upper()})")

        # 6. Preenchimento / Tratamento de Nulos
        if req.fill_nulls:
            for op in req.fill_nulls:
                if op.column not in df.columns:
                    continue
                if op.strategy == "drop_rows":
                    df = df.filter(pl.col(op.column).is_not_null())
                    applied_steps.append(f"Linhas com nulo em '{op.column}' foram removidas")
                elif op.strategy == "value" and op.fill_value is not None:
                    df = df.with_columns(pl.col(op.column).fill_null(op.fill_value))
                    applied_steps.append(f"Nulos em '{op.column}' preenchidos com '{op.fill_value}'")
                elif op.strategy in ["mean", "median"]:
                    val = df[op.column].mean() if op.strategy == "mean" else df[op.column].median()
                    if val is not None:
                        df = df.with_columns(pl.col(op.column).fill_null(val))
                        applied_steps.append(f"Nulos em '{op.column}' preenchidos com a {op.strategy}: {round(val, 2)}")
                elif op.strategy in ["ffill", "bfill"]:
                    strategy_op = pl.col(op.column).forward_fill() if op.strategy == "ffill" else pl.col(op.column).backward_fill()
                    df = df.with_columns(strategy_op)
                    applied_steps.append(f"Nulos em '{op.column}' preenchidos por {op.strategy}")

        # 7. Conversão de Tipos (Cast)
        if req.type_casts:
            for op in req.type_casts:
                if op.column not in df.columns:
                    continue
                target_map = {
                    "Utf8": pl.Utf8,
                    "Int64": pl.Int64,
                    "Float64": pl.Float64,
                    "Date": pl.Date,
                    "Boolean": pl.Boolean
                }
                dtype = target_map.get(op.target_type)
                if dtype:
                    df = df.with_columns(pl.col(op.column).cast(dtype, strict=False))
                    applied_steps.append(f"Coluna '{op.column}' convertida para {op.target_type}")

        # 8. Renomear Colunas
        if req.rename_columns:
            rename_dict = {op.old_name: op.new_name for op in req.rename_columns if op.old_name in df.columns}
            if rename_dict:
                df = df.rename(rename_dict)
                applied_steps.append(f"Renomeadas colunas: {rename_dict}")

        # Salvar dataset limpo
        clean_dataset_id = req.dataset_id if req.overwrite_original else f"{req.dataset_id}_clean"
        output_path = os.path.join(STORAGE_DIR, f"{clean_dataset_id}.parquet")
        df.write_parquet(output_path)

        cleaned_rows = df.height
        cleaned_cols = df.width

        return TransformationResultResponse(
            dataset_id=req.dataset_id,
            clean_dataset_id=clean_dataset_id,
            original_rows=original_rows,
            cleaned_rows=cleaned_rows,
            removed_rows=original_rows - cleaned_rows,
            original_cols=original_cols,
            cleaned_cols=cleaned_cols,
            applied_steps=applied_steps
        )