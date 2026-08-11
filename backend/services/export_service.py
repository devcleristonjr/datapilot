# datapilot/backend/services/export_service.py
import os
import polars as pl
from fastapi import HTTPException
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from services.ai_service import AIService
from services.profiler_service import ProfilerService

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")


class ExportService:

    @classmethod
    def _get_dataset_file(cls, dataset_id: str) -> str:
        """Prioriza o dataset limpo (_clean.parquet). Se não existir, utiliza o original."""
        clean_path = os.path.join(STORAGE_DIR, f"{dataset_id}_clean.parquet")
        orig_path = os.path.join(STORAGE_DIR, f"{dataset_id}.parquet")

        if os.path.exists(clean_path):
            return clean_path
        if os.path.exists(orig_path):
            return orig_path

        raise HTTPException(status_code=404, detail="Dataset não encontrado.")

    @classmethod
    def export_csv(cls, dataset_id: str) -> str:
        file_path = cls._get_dataset_file(dataset_id)
        df = pl.read_parquet(file_path)

        out_path = os.path.join(STORAGE_DIR, f"{dataset_id}_export.csv")
        df.write_csv(out_path)
        return out_path

    @classmethod
    def export_excel(cls, dataset_id: str) -> str:
        file_path = cls._get_dataset_file(dataset_id)
        df = pl.read_parquet(file_path)

        out_path = os.path.join(STORAGE_DIR, f"{dataset_id}_export.xlsx")
        df.write_excel(out_path)
        return out_path

    @classmethod
    def generate_pdf_report(cls, dataset_id: str) -> str:
        # Obter dados consolidados do Profiler e do DataPilot AI
        diagnostic = AIService.diagnose_dataset(dataset_id)
        profile = ProfilerService.generate_profile(dataset_id)

        pdf_path = os.path.join(STORAGE_DIR, f"{dataset_id}_report.pdf")

        # Configuração do documento A4
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0F172A'),
            bold=True
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#64748B')
        )
        h2_style = ParagraphStyle(
            'H2Style',
            parent=styles['Heading2'],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#1E293B'),
            bold=True,
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155')
        )

        elements = []

        # Header / Cabeçalho
        elements.append(Paragraph("DATAPILOT AI — Relatório de Qualidade de Dados", title_style))
        elements.append(Paragraph(f"Dataset ID: {dataset_id} | Diagnóstico Automático", subtitle_style))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceAfter=10))

        # Tabela de Resumo / Score
        score_data = [
            [
                Paragraph(f"<b>Score de Qualidade:</b><br/>{diagnostic.quality_score}/100", body_style),
                Paragraph(f"<b>Status de Saúde:</b><br/>{diagnostic.health_status}", body_style),
                Paragraph(f"<b>Total de Linhas:</b><br/>{profile.total_rows:,}", body_style),
                Paragraph(f"<b>Total de Colunas:</b><br/>{profile.total_columns}", body_style)
            ]
        ]
        score_table = Table(score_data, colWidths=[130, 130, 130, 130])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 10))

        # Resumo Executivo
        elements.append(Paragraph("1. Resumo Executivo", h2_style))
        elements.append(Paragraph(diagnostic.executive_summary, body_style))
        elements.append(Spacer(1, 8))

        # Destaques da Base
        if diagnostic.key_findings:
            elements.append(Paragraph("2. Principais Achados na Base", h2_style))
            for finding in diagnostic.key_findings:
                elements.append(Paragraph(f"• {finding}", body_style))
            elements.append(Spacer(1, 8))

        # Lista de Problemas Detectados
        if diagnostic.issues:
            elements.append(Paragraph("3. Problemas de Qualidade Identificados", h2_style))
            issues_table_data = [["Severidade", "Tipo de Falha", "Coluna", "Descrição"]]

            for issue in diagnostic.issues:
                issues_table_data.append([
                    issue.severity.upper(),
                    issue.issue_type,
                    issue.column or "N/A",
                    Paragraph(issue.description, body_style)
                ])

            issues_table = Table(issues_table_data, colWidths=[70, 110, 90, 250])
            issues_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('PADDING', (0, 1), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(issues_table)
            elements.append(Spacer(1, 10))

        # Insights Potenciais
        if diagnostic.potential_insights:
            elements.append(Paragraph("4. Estatísticas Executivas Gerais", h2_style))
            for insight in diagnostic.potential_insights:
                elements.append(Paragraph(f"• {insight}", body_style))

        # Construir arquivo PDF
        doc.build(elements)
        return pdf_path