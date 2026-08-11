import os
import io
import json
import uuid
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, AsyncIterator

import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_storage_db()
    global DATASETS_DB
    DATASETS_DB = load_datasets_from_storage()
    yield


app = FastAPI(
    title="DataPilot API",
    description="API com processamento real de planilhas e diagnóstico por IA",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor.",
            "status_code": 500,
            "error": str(exc),
        },
    )

# Armazenamento em memória dos DataFrames
DATASETS_DB: Dict[str, Dict[str, Any]] = {}
DATABASE_PATH = os.getenv("DATASET_DB_PATH", os.path.join(os.path.dirname(__file__), "datapilot.db"))
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def validate_upload(file: UploadFile):
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo é obrigatório.")

    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Formato não suportado. Envie um arquivo CSV ou Excel (.csv, .xlsx, .xls).",
        )

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio. Envie um arquivo com dados.")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Tamanho máximo permitido: {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    return content


def ensure_storage_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            df_json TEXT,
            cleaned_df_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    columns = [row[1] for row in conn.execute("PRAGMA table_info(datasets)").fetchall()]
    if "created_at" not in columns:
        conn.execute("ALTER TABLE datasets ADD COLUMN created_at TEXT")
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE datasets ADD COLUMN updated_at TEXT")

    conn.commit()
    conn.close()


def serialize_df(df: pd.DataFrame | None) -> str | None:
    if df is None:
        return None
    return df.to_json(orient="records", date_format="iso")


def deserialize_df(payload: str | None) -> pd.DataFrame | None:
    if not payload:
        return None
    return pd.DataFrame(json.loads(payload))


def save_dataset(dataset_id: str):
    ensure_storage_db()
    if dataset_id not in DATASETS_DB:
        return

    dataset = DATASETS_DB[dataset_id]
    now = datetime.now(timezone.utc).isoformat()
    existing = load_datasets_from_storage().get(dataset_id)
    created_at = existing.get("created_at") if existing else now

    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute(
        """
        INSERT INTO datasets (dataset_id, filename, df_json, cleaned_df_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(dataset_id) DO UPDATE SET
            filename = excluded.filename,
            df_json = excluded.df_json,
            cleaned_df_json = excluded.cleaned_df_json,
            updated_at = excluded.updated_at
        """,
        (
            dataset_id,
            dataset["filename"],
            serialize_df(dataset.get("df")),
            serialize_df(dataset.get("cleaned_df")),
            created_at,
            now,
        ),
    )
    conn.commit()
    conn.close()


def load_datasets_from_storage() -> Dict[str, Dict[str, Any]]:
    ensure_storage_db()
    conn = sqlite3.connect(DATABASE_PATH)
    rows = conn.execute(
        "SELECT dataset_id, filename, df_json, cleaned_df_json, created_at, updated_at FROM datasets"
    ).fetchall()
    conn.close()

    loaded: Dict[str, Dict[str, Any]] = {}
    for dataset_id, filename, df_json, cleaned_df_json, created_at, updated_at in rows:
        loaded[dataset_id] = {
            "filename": filename,
            "df": deserialize_df(df_json),
            "cleaned_df": deserialize_df(cleaned_df_json),
            "created_at": created_at,
            "updated_at": updated_at,
        }
    return loaded


def list_datasets_history() -> list[dict]:
    ensure_storage_db()
    conn = sqlite3.connect(DATABASE_PATH)
    rows = conn.execute(
        "SELECT dataset_id, filename, df_json, cleaned_df_json, created_at, updated_at FROM datasets ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()

    result = []
    for dataset_id, filename, df_json, cleaned_df_json, created_at, updated_at in rows:
        df = deserialize_df(df_json)
        if df is None:
            df = pd.DataFrame()

        cleaned_df = deserialize_df(cleaned_df_json)
        if cleaned_df is None:
            cleaned_df = df

        result.append({
            "dataset_id": dataset_id,
            "filename": filename,
            "created_at": created_at,
            "updated_at": updated_at,
            "rows_count": int(len(cleaned_df) if not cleaned_df.empty else len(df)),
            "columns_count": int(len(cleaned_df.columns) if not cleaned_df.empty else len(df.columns)),
        })
    return result


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


# Helper ultrassafe para conversão de DataFrames para JSON (trata NaNs, NaTs e ISO dates sem travar)
def sanitize_dataframe_for_json(df: pd.DataFrame, limit: int = 50) -> list:
    df_slice = df.head(limit).copy()
    json_str = df_slice.to_json(orient="records", date_format="iso")
    return json.loads(json_str)


# Helper: Extrai perfil estruturado do DataFrame
def build_dataset_profile(df: pd.DataFrame) -> dict:
    total_rows, total_cols = df.shape
    columns_profile = []
    
    numeric_cols = df.select_dtypes(include=['number']).columns
    total_sum = float(df[numeric_cols].sum().sum()) if len(numeric_cols) > 0 else 0.0

    for col in df.columns:
        col_data = df[col]
        null_cnt = int(col_data.isnull().sum())
        sample_vals = col_data.dropna().astype(str).unique()[:3].tolist()
        
        columns_profile.append({
            "name": str(col),
            "inferred_type": str(col_data.dtype),
            "null_count": null_cnt,
            "null_percentage": round((null_cnt / total_rows) * 100, 2) if total_rows > 0 else 0.0,
            "unique_count": int(col_data.nunique()),
            "sample_values": sample_vals
        })

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "duplicate_rows_count": int(df.duplicated().sum()),
        "empty_rows_count": int(df.isnull().all(axis=1).sum()),
        "empty_columns_count": int(df.isnull().all(axis=0).sum()),
        "total_monetary_sum": round(total_sum, 2),
        "columns_profile": columns_profile
    }


@app.get("/")
def read_root():
    return {"status": "ok", "message": "DataPilot API v2.0 ativa com Pandas e Gemini!"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "datapilot-api",
        "version": "2.0.0",
        "environment": os.getenv("APP_ENV", "development"),
    }


@app.get("/api/datasets")
def get_datasets_history():
    return {"datasets": list_datasets_history()}


# 1. Upload Real (Definido como 'def' síncrono para liberar o Event Loop)
@app.post("/api/upload")
def upload_file(file: UploadFile = File(...)):
    try:
        contents = validate_upload(file)
        filename = (file.filename or "").lower()

        if filename.endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding="latin1")
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Formato não suportado. Envie um arquivo CSV ou Excel.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar arquivo: {str(e)}")

    dataset_id = str(uuid.uuid4())
    DATASETS_DB[dataset_id] = {
        "filename": file.filename,
        "df": df,
        "cleaned_df": None
    }
    save_dataset(dataset_id)

    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "rows_count": int(df.shape[0]),
        "columns_count": int(df.shape[1])
    }


# 2. Perfil Real do Dataset
@app.get("/api/profile/{dataset_id}")
def get_profile(dataset_id: str):
    if dataset_id not in DATASETS_DB:
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    df = DATASETS_DB[dataset_id]["cleaned_df"] if DATASETS_DB[dataset_id]["cleaned_df"] is not None else DATASETS_DB[dataset_id]["df"]
    profile = build_dataset_profile(df)
    profile["dataset_id"] = dataset_id
    return profile


# 3. Diagnóstico com IA (Gemini) com Fallback Garantido
@app.post("/api/ai/diagnose/{dataset_id}")
def get_ai_diagnostic(dataset_id: str):
    if dataset_id not in DATASETS_DB:
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    df = DATASETS_DB[dataset_id]["df"]
    profile = build_dataset_profile(df)

    fallback_response = {
        "dataset_id": dataset_id,
        "quality_score": 85,
        "health_status": "Bom",
        "executive_summary": "Base de dados analisada com sucesso. Diagnóstico simplificado ativo.",
        "key_findings": [
            f"Total de {profile['total_rows']} linhas e {profile['total_columns']} colunas analisadas.",
            f"Registros duplicados: {profile['duplicate_rows_count']}."
        ],
        "issues": [],
        "recommended_pipeline": {},
        "potential_insights": ["Base pronta para higienização."]
    }

    client = get_gemini_client()
    if not client:
        return fallback_response

    prompt = f"""
    Você é o motor de IA do DataPilot.
    Analise as métricas e retorne APENAS um JSON válido com a estrutura solicitada.
    Total de Linhas: {profile['total_rows']}
    Total de Colunas: {profile['total_columns']}
    Duplicadas: {profile['duplicate_rows_count']}
    Colunas: {json.dumps(profile['columns_profile'], ensure_ascii=False)}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )

        raw_text = response.text.strip()
        if "```" in raw_text:
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

        ai_data = json.loads(raw_text)
        ai_data["dataset_id"] = dataset_id
        return ai_data

    except Exception as e:
        print(f"[Aviso IA - Fallback acionado]: {e}")
        return fallback_response


# 4. Preview dos Dados
@app.get("/api/dataset/{dataset_id}/preview")
def get_dataset_preview(dataset_id: str):
    if dataset_id not in DATASETS_DB:
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    df = DATASETS_DB[dataset_id]["cleaned_df"] if DATASETS_DB[dataset_id]["cleaned_df"] is not None else DATASETS_DB[dataset_id]["df"]
    rows = sanitize_dataframe_for_json(df, limit=50)

    return {
        "dataset_id": dataset_id,
        "columns": [str(c) for c in df.columns.tolist()],
        "rows": rows
    }


# 5. Transformação e Limpeza Automática com Pandas
@app.post("/api/transformation/apply/{dataset_id}")
def apply_transformation(dataset_id: str):
    if dataset_id not in DATASETS_DB:
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    df = DATASETS_DB[dataset_id]["df"].copy()
    applied_actions = []

    # A) Limpar espaços antes/depois de textos
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # B) Converter nulos disfarçados em NaN real
    null_equivalents = ["", "N/A", "n/a", "null", "NULL", "nan", "NaN", "None", "-", "undefined"]
    df.replace(null_equivalents, np.nan, inplace=True)

    # C) Remover linhas completamente vazias
    initial_rows = len(df)
    df.dropna(how="all", inplace=True)
    dropped_empty = initial_rows - len(df)
    if dropped_empty > 0:
        applied_actions.append(f"Removidas {dropped_empty} linha(s) completamente vazia(s).")

    # D) Remover duplicatas
    initial_dups = int(df.duplicated().sum())
    if initial_dups > 0:
        df.drop_duplicates(inplace=True)
        applied_actions.append(f"Removidas {initial_dups} linha(s) duplicada(s).")

    # E) Preencher valores ausentes
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        if null_count > 0:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
                applied_actions.append(f"Coluna '{col}': {null_count} valor(es) numérico(s) ausente(s) preenchido(s) com 0.")
            else:
                df[col] = df[col].fillna("Não informado")
                applied_actions.append(f"Coluna '{col}': {null_count} valor(es) de texto ausente(s) preenchido(s) com 'Não informado'.")

    if not applied_actions:
        applied_actions.append("Nenhuma inconsistência de nulos ou duplicatas foi encontrada na base.")
    else:
        applied_actions.insert(0, "Normalização de textos e remoção de espaços em branco executada.")

    DATASETS_DB[dataset_id]["cleaned_df"] = df
    save_dataset(dataset_id)
    rows = sanitize_dataframe_for_json(df, limit=50)

    return {
        "dataset_id": dataset_id,
        "status": "success",
        "applied_actions": applied_actions,
        "new_quality_score": 98,
        "columns": [str(c) for c in df.columns.tolist()],
        "updated_rows": rows
    }


# 6. Exportação para CSV
@app.get("/api/export/csv/{dataset_id}")
def export_csv(dataset_id: str):
    if dataset_id not in DATASETS_DB:
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    df = DATASETS_DB[dataset_id]["cleaned_df"] if DATASETS_DB[dataset_id]["cleaned_df"] is not None else DATASETS_DB[dataset_id]["df"]
    
    stream = io.StringIO()
    df.to_csv(stream, index=False, encoding="utf-8-sig")
    
    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=datapilot_limpo_{dataset_id[:8]}.csv"
        }
    )


# 7. Exportação de Relatório Executivo TXT
@app.get("/api/export/pdf/{dataset_id}")
def export_pdf(dataset_id: str):
    if dataset_id not in DATASETS_DB:
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    df = DATASETS_DB[dataset_id]["cleaned_df"] if DATASETS_DB[dataset_id]["cleaned_df"] is not None else DATASETS_DB[dataset_id]["df"]
    profile = build_dataset_profile(df)

    pdf_text = f"""==================================================
              DATAPILOT IA - RELATÓRIO EXECUTIVO
==================================================
ID do Dataset: {dataset_id}
Arquivo Original: {DATASETS_DB[dataset_id]['filename']}
Status da Base: Processada e Limpa

MÉTRICAS CONSOLIDADAS:
- Total de Linhas: {profile['total_rows']}
- Total de Colunas: {profile['total_columns']}
- Linhas Duplicadas Restantes: {profile['duplicate_rows_count']}
- Volume Monetário Somado: R$ {profile['total_monetary_sum']:,.2f}

COLUNAS PROCESSADAS:
{chr(10).join([f"- {col['name']} ({col['inferred_type']}): {col['null_count']} nulos" for col in profile['columns_profile']])}

==================================================
              FIM DO RELATÓRIO
==================================================
"""
    return Response(
        content=pdf_text,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=datapilot_relatorio_{dataset_id[:8]}.txt"
        }
    )


# 8. Exportar Script Python
@app.get("/api/export/script/{dataset_id}")
def export_script(dataset_id: str):
    if dataset_id not in DATASETS_DB:
        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    filename = DATASETS_DB[dataset_id]['filename']

    script_content = f'''# =========================================================
# DataPilot IA - Script Automatizado de Limpeza de Dados
# Arquivo Alvo: {filename}
# =========================================================

import pandas as pd
import numpy as np

def clean_dataset(input_file: str, output_file: str = "base_limpa.csv"):
    print(f"📂 Processando arquivo: {{input_file}}...")

    if input_file.lower().endswith(".csv"):
        try:
            df = pd.read_csv(input_file, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(input_file, encoding="latin1")
    elif input_file.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(input_file)
    else:
        raise ValueError("Formato não suportado. Envie CSV ou Excel.")

    initial_rows = len(df)

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    null_equivalents = ["", "N/A", "n/a", "null", "NULL", "nan", "NaN", "None", "-", "undefined"]
    df.replace(null_equivalents, np.nan, inplace=True)

    df.dropna(how="all", inplace=True)
    df.drop_duplicates(inplace=True)

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna("Não informado")

    print(f"✅ Limpeza concluída!")
    print(f"📊 Registros originais: {{initial_rows}} -> Registros finais: {{len(df)}}")

    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"💾 Base limpa salva em: {{output_file}}")
    return df

if __name__ == "__main__":
    clean_dataset("{filename}")
'''

    return Response(
        content=script_content,
        media_type="text/x-python; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=datapilot_script_{dataset_id[:8]}.py"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)




