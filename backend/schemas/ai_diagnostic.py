# datapilot/backend/schemas/ai_diagnostic.py
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from schemas.transformation import TransformationPipelineRequest


class QualityIssue(BaseModel):
    severity: Literal["critical", "warning", "info"]
    issue_type: str
    column: Optional[str] = None
    description: str
    suggested_action: str


class AIDiagnosticResponse(BaseModel):
    dataset_id: str
    quality_score: int = Field(ge=0, le=100, description="Score global de qualidade de 0 a 100")
    health_status: Literal["Excelente", "Bom", "Atenção Necessária", "Crítico"]
    executive_summary: str
    key_findings: List[str]
    issues: List[QualityIssue]
    recommended_pipeline: TransformationPipelineRequest
    potential_insights: List[str]