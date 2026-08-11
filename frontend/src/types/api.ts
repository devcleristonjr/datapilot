export interface ColumnProfile {
  name: string;
  inferred_type: string;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: string[];
}

export interface DatasetProfile {
  dataset_id: string;
  total_rows: number;
  total_columns: number;
  duplicate_rows_count: number;
  empty_rows_count: number;
  empty_columns_count: number;
  total_monetary_sum?: number;
  unique_municipalities_count?: number;
  unique_organs_count?: number;
  columns_profile: ColumnProfile[];
}

export interface AIDiagnosticResponse {
  dataset_id: string;
  quality_score: number;
  health_status: string;
  executive_summary: string;
  key_findings: string[];
  issues: string[];
  recommended_pipeline?: Record<string, any>;
  potential_insights?: string[];
}

export interface DatasetPreviewResponse {
  dataset_id: string;
  columns: string[];
  rows: Record<string, any>[];
}

export interface UploadResponse {
  dataset_id: string;
  filename: string;
  rows_count: number;
  columns_count: number;
}

export interface TransformationResponse {
  dataset_id: string;
  status: string;
  applied_actions: string[];
  new_quality_score: number;
  columns?: string[];
  updated_rows: Record<string, any>[];
}