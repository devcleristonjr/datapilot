# backend/services/profiler_service.py
import os
import re
import math
import polars as pl
from typing import Optional, Any
from fastapi import HTTPException
from schemas.profile import ColumnProfile, DatasetProfile

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")

class ProfilerService:
    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        """Converte um valor para float seguro (trata None, NaN e Infinity para evitar erro de JSON)."""
        if val is None:
            return None
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return None
            return round(f, 2)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_currency_string(expr: pl.Expr) -> pl.Expr:
        """Limpa strings no formato 'R$ 1.234,56' e converte para Float64."""
        return (
            expr.cast(pl.Utf8, strict=False)
                .str.replace_all(r"[R$\s]", "")
                .str.replace_all(r"\.", "")
                .str.replace(",", ".")
                .cast(pl.Float64, strict=False)
        )

    @staticmethod
    def _detect_type_and_stats(df: pl.DataFrame, col_name: str) -> ColumnProfile:
        col = df[col_name]
        raw_type = str(col.dtype)
        total_rows = df.height

        # Conversão segura para string para verificar valores vazios
        col_str = col.cast(pl.Utf8, strict=False)
        invalid_mask = col.is_null() | col_str.is_in(["", "N/A", "null", "None", "nan", "NaN"])
        null_count = int(invalid_mask.sum())
        null_percentage = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0.0
        unique_count = col.n_unique()

        inferred_type = "text"
        min_val, max_val, sum_val, mean_val, median_val = None, None, None, None, None

        # Sample dos dados não nulos para inferência de padrão
        valid_samples = col_str.filter(~invalid_mask).head(100).to_list()
        sample = [str(x).strip() for x in valid_samples if str(x).strip()]

        is_numeric = False
        parsed_series = None

        # 1. Checagem de Tipo Monetário / Numérico
        if col.dtype in [pl.Int64, pl.Int32, pl.Int16, pl.Int8, pl.Float64, pl.Float32]:
            is_numeric = True
            inferred_type = "number"
            parsed_series = col.cast(pl.Float64, strict=False)
        elif len(sample) > 0:
            if any("R$" in x or re.search(r"^\d{1,3}(\.\d{3})*,\d{2}$", x) for x in sample):
                parsed_series = df.select(ProfilerService._clean_currency_string(pl.col(col_name)))[col_name]
                if parsed_series.drop_nulls().len() > 0:
                    is_numeric = True
                    inferred_type = "currency"

        if is_numeric and parsed_series is not None:
            valid_numeric = parsed_series.drop_nulls()
            if valid_numeric.len() > 0:
                min_val = ProfilerService._safe_float(valid_numeric.min())
                max_val = ProfilerService._safe_float(valid_numeric.max())
                sum_val = ProfilerService._safe_float(valid_numeric.sum())
                mean_val = ProfilerService._safe_float(valid_numeric.mean())
                median_val = ProfilerService._safe_float(valid_numeric.median())

        # 2. Checagem de CPF / CNPJ / Data / Município (caso não seja numérico)
        if not is_numeric and len(sample) > 0:
            col_upper = col_name.upper()

            cpf_pattern = re.compile(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$")
            cnpj_pattern = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$")
            date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}$")

            matches_cpf = sum(1 for x in sample if cpf_pattern.match(x))
            matches_cnpj = sum(1 for x in sample if cnpj_pattern.match(x))
            matches_date = sum(1 for x in sample if date_pattern.match(x))

            if matches_cpf / len(sample) > 0.5 or "CPF" in col_upper:
                inferred_type = "cpf"
            elif matches_cnpj / len(sample) > 0.5 or "CNPJ" in col_upper:
                inferred_type = "cnpj"
            elif matches_date / len(sample) > 0.5 or "DATA" in col_upper:
                inferred_type = "date"
            elif "MUNICIPIO" in col_upper or "MUNICÍPIO" in col_upper:
                inferred_type = "municipio"
            elif "ÓRGÃO" in col_upper or "ORGAO" in col_upper:
                inferred_type = "organ"
            elif "SITUAÇÃO" in col_upper or "SITUACAO" in col_upper:
                inferred_type = "situation"

        return ColumnProfile(
            name=col_name,
            raw_type=raw_type,
            inferred_type=inferred_type,
            null_count=null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
            min_value=min_val,
            max_value=max_val,
            sum_value=sum_val,
            mean_value=mean_val,
            median_value=median_val,
        )

    @classmethod
    def generate_profile(cls, dataset_id: str) -> DatasetProfile:
        parquet_path = os.path.join(STORAGE_DIR, f"{dataset_id}.parquet")

        if not os.path.exists(parquet_path):
            raise HTTPException(status_code=404, detail="Dataset não encontrado.")

        df = pl.read_parquet(parquet_path)
        total_rows = df.height
        total_columns = df.width

        # Detecção de perfis de coluna
        columns_profile = [cls._detect_type_and_stats(df, col) for col in df.columns]

        # Contagem segura de linhas vazias
        empty_rows_count = df.filter(
            pl.all_horizontal(
                pl.all().is_null() | (pl.all().cast(pl.Utf8, strict=False).str.strip_chars() == "")
            )
        ).height

        empty_columns_count = sum(1 for cp in columns_profile if cp.null_count == total_rows)
        duplicate_rows_count = total_rows - df.unique().height

        # Métricas globais consolidadas
        total_monetary_sum = sum(
            cp.sum_value for cp in columns_profile if cp.sum_value is not None and cp.inferred_type == "currency"
        )

        unique_municipalities = 0
        unique_organs = 0
        unique_situations = 0

        for cp in columns_profile:
            if cp.inferred_type == "municipio":
                unique_municipalities = cp.unique_count
            elif cp.inferred_type == "organ":
                unique_organs = cp.unique_count
            elif cp.inferred_type == "situation":
                unique_situations = cp.unique_count

        return DatasetProfile(
            dataset_id=dataset_id,
            total_rows=total_rows,
            total_columns=total_columns,
            empty_rows_count=empty_rows_count,
            empty_columns_count=empty_columns_count,
            duplicate_rows_count=duplicate_rows_count,
            total_monetary_sum=round(total_monetary_sum, 2),
            unique_municipalities_count=unique_municipalities,
            unique_organs_count=unique_organs,
            unique_situations_count=unique_situations,
            columns_profile=columns_profile
        )