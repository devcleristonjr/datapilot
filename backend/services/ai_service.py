# datapilot/backend/services/ai_service.py
from typing import List
from schemas.profile import DatasetProfile
from schemas.ai_diagnostic import AIDiagnosticResponse, QualityIssue
from schemas.transformation import (
    TransformationPipelineRequest,
    FillNullsOp,
    StandardizeTextOp,
    StandardizeIdentifierOp,
    RenameColumnOp,
)
from services.profiler_service import ProfilerService


class AIService:

    @classmethod
    def diagnose_dataset(cls, dataset_id: str) -> AIDiagnosticResponse:
        # 1. Obter o perfil do dataset
        profile: DatasetProfile = ProfilerService.generate_profile(dataset_id)

        total_rows = profile.total_rows
        total_cols = profile.total_columns

        issues: List[QualityIssue] = []
        key_findings: List[str] = []
        potential_insights: List[str] = []

        # Listas para construir a recomendação de pipeline automaticamente
        fill_nulls_ops: List[FillNullsOp] = []
        text_ops: List[StandardizeTextOp] = []
        id_ops: List[StandardizeIdentifierOp] = []
        rename_ops: List[RenameColumnOp] = []
        drop_cols: List[str] = []

        # Cálculo Inicial do Score de Qualidade (Base 100)
        score_penalty = 0.0

        # --- ANÁLISE DE DUPLICATAS ---
        if profile.duplicate_rows_count > 0:
            dup_pct = (profile.duplicate_rows_count / total_rows) * 100 if total_rows > 0 else 0
            severity = "critical" if dup_pct > 10 else ("warning" if dup_pct > 1 else "info")
            penalty = 20 if severity == "critical" else (10 if severity == "warning" else 5)
            score_penalty += penalty

            issues.append(
                QualityIssue(
                    severity=severity,
                    issue_type="Linhas Duplicadas",
                    description=f"Foram identificadas {profile.duplicate_rows_count} linhas duplicadas ({round(dup_pct, 1)}% da base).",
                    suggested_action="Ativar a remoção de duplicatas no pipeline de limpeza."
                )
            )
            key_findings.append(f"Base contém {profile.duplicate_rows_count} registros idênticos que podem distorcer agregações.")

        # --- ANÁLISE DE LINHAS/COLUNAS VAZIAS ---
        if profile.empty_rows_count > 0:
            score_penalty += 5
            issues.append(
                QualityIssue(
                    severity="warning",
                    issue_type="Linhas Vazias",
                    description=f"Existem {profile.empty_rows_count} linhas completamente vazias no arquivo.",
                    suggested_action="Remover linhas totalmente vazias automaticamente."
                )
            )

        if profile.empty_columns_count > 0:
            score_penalty += 10
            key_findings.append(f"{profile.empty_columns_count} coluna(s) não possuem nenhum dado preenchido.")

        # --- ANÁLISE DE COLUNAS INDIVIDUAIS ---
        for col in profile.columns_profile:
            c_name = col.name
            null_pct = col.null_percentage

            # 1. Colunas 100% nulas
            if null_pct == 100.0:
                drop_cols.append(c_name)
                issues.append(
                    QualityIssue(
                        severity="warning",
                        issue_type="Coluna Sem Dados",
                        column=c_name,
                        description=f"A coluna '{c_name}' está completamente vazia (100% de nulos).",
                        suggested_action="Remover a coluna do dataset final."
                    )
                )
                continue

            # 2. Alto percentual de nulos
            if null_pct > 30.0:
                severity = "critical" if null_pct > 60 else "warning"
                score_penalty += 8 if severity == "critical" else 4
                issues.append(
                    QualityIssue(
                        severity=severity,
                        issue_type="Muitos Nulos",
                        column=c_name,
                        description=f"A coluna '{c_name}' possui {null_pct}% de valores ausentes.",
                        suggested_action="Preencher com valor padrão/estatístico ou filtrar nulos."
                    )
                )

                # Sugestão no pipeline conforme o tipo
                if col.inferred_type in ["number", "currency"]:
                    fill_nulls_ops.append(FillNullsOp(column=c_name, strategy="median"))
                else:
                    fill_nulls_ops.append(FillNullsOp(column=c_name, strategy="value", fill_value="NÃO INFORMADO"))
            elif null_pct > 0:
                # Nulos leves
                if col.inferred_type in ["number", "currency"]:
                    fill_nulls_ops.append(FillNullsOp(column=c_name, strategy="median"))
                else:
                    fill_nulls_ops.append(FillNullsOp(column=c_name, strategy="value", fill_value="NÃO INFORMADO"))

            # 3. Formatação e Padronização
            if col.inferred_type == "currency":
                id_ops.append(StandardizeIdentifierOp(column=c_name, id_type="currency"))
                key_findings.append(f"Coluna monetária '{c_name}' detectada (Soma estimada: R$ {profile.total_monetary_sum:,.2f}).")
            elif col.inferred_type in ["cpf", "cnpj"]:
                id_ops.append(StandardizeIdentifierOp(column=c_name, id_type=col.inferred_type))
                key_findings.append(f"Identificador corporativo '{c_name}' ({col.inferred_type.upper()}) precisa de higienização de pontuação.")

            if col.inferred_type in ["text", "municipio", "organ", "situation"]:
                text_ops.append(StandardizeTextOp(column=c_name, action="trim"))
                if col.inferred_type == "municipio":
                    text_ops.append(StandardizeTextOp(column=c_name, action="uppercase"))

            # Nomes de colunas com caracteres problemáticos
            if any(char in c_name for char in [" ", "-", "/", "."]):
                clean_name = c_name.lower().strip().replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "_")
                rename_ops.append(RenameColumnOp(old_name=c_name, new_name=clean_name))

        # --- CALCULAR SCORE E STATUS FINAL ---
        quality_score = max(0, min(100, int(100 - score_penalty)))

        if quality_score >= 85:
            health_status = "Excelente"
        elif quality_score >= 70:
            health_status = "Bom"
        elif quality_score >= 50:
            health_status = "Atenção Necessária"
        else:
            health_status = "Crítico"

        # --- DESTAQUES DE INSIGHTS ANALÍTICOS ---
        if profile.total_monetary_sum > 0:
            potential_insights.append(f"Volume financeiro total identificado na base: R$ {profile.total_monetary_sum:,.2f}.")
        if profile.unique_municipalities_count > 0:
            potential_insights.append(f"A base abrange {profile.unique_municipalities_count} município(s) distintos.")
        if profile.unique_organs_count > 0:
            potential_insights.append(f"Foram mapeados {profile.unique_organs_count} órgão(s) / secretaria(s) responsáveis.")

        potential_insights.append(f"O arquivo possui {total_rows:,} registros distribuídos em {total_cols} colunas.")

        # Resumo executivo em linguagem natural
        executive_summary = (
            f"O dataset apresenta {total_rows} linhas e {total_cols} colunas com status geral '{health_status}' "
            f"(Score: {quality_score}/100). Foram identificados {len(issues)} ponto(s) de atenção que demandam "
            f"tratamento antes das análises executivas."
        )

        # Montar recomendação do pipeline
        recommended_pipeline = TransformationPipelineRequest(
            dataset_id=dataset_id,
            drop_columns=drop_cols,
            remove_duplicates=profile.duplicate_rows_count > 0,
            drop_empty_rows=profile.empty_rows_count > 0,
            fill_nulls=fill_nulls_ops,
            text_standardizations=text_ops,
            identifier_standardizations=id_ops,
            rename_columns=rename_ops,
            overwrite_original=False
        )

        return AIDiagnosticResponse(
            dataset_id=dataset_id,
            quality_score=quality_score,
            health_status=health_status,
            executive_summary=executive_summary,
            key_findings=key_findings,
            issues=issues,
            recommended_pipeline=recommended_pipeline,
            potential_insights=potential_insights
        )