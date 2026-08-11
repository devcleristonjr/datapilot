import {
  UploadResponse,
  DatasetProfile,
  AIDiagnosticResponse,
  DatasetPreviewResponse,
  TransformationResponse,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

async function customFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

  const isGet = !options?.method || options.method.toUpperCase() === "GET";

  // Define Content-Type apenas para requisições com corpo
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  };

  if (!isGet && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  try {
    console.log(`[API Request] ${options?.method || "GET"} -> ${url}`);
    
    const res = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Erro no servidor (Status ${res.status})`);
    }

    return await res.json();
  } catch (err: any) {
    clearTimeout(timeoutId);

    if (err.name === "AbortError") {
      console.error(`[API Error] Timeout excedido em ${url}`);
      throw new Error("O servidor demorou muito para responder (Timeout).");
    }

    if (err.name === "TypeError" && err.message === "Failed to fetch") {
      console.error(`[API Error] Falha de conexão/CORS em ${url}`);
      throw new Error(
        `Servidor offline ou bloqueio de CORS em "${API_BASE_URL}". Verifique se o backend Python está ativo e com CORS liberado.`
      );
    }
    throw err;
  }
}

async function downloadBlob(url: string, defaultFilename: string): Promise<void> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Falha ao gerar arquivo (Status ${res.status})`);
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = downloadUrl;
    link.download = defaultFilename;
    document.body.appendChild(link);
    link.click();

    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  } catch (err: any) {
    clearTimeout(timeoutId);
    throw err;
  }
}

export interface DatasetHistoryEntry {
  dataset_id: string;
  filename: string;
  created_at: string | null;
  updated_at: string | null;
  rows_count: number;
  columns_count: number;
}

export const DataPilotAPI = {
  async getDatasetHistory(): Promise<DatasetHistoryEntry[]> {
    const response = await customFetch<{ datasets: DatasetHistoryEntry[] }>(`${API_BASE_URL}/api/datasets`);
    return response.datasets || [];
  },

  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 20000);

    try {
      const res = await fetch(`${API_BASE_URL}/api/upload`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Erro no upload (Status ${res.status})`);
      }
      return await res.json();
    } catch (err: any) {
      clearTimeout(timeoutId);
      throw err;
    }
  },

  async getProfile(datasetId: string): Promise<DatasetProfile> {
    const id = encodeURIComponent(datasetId);
    return customFetch<DatasetProfile>(`${API_BASE_URL}/api/profile/${id}`);
  },

  async getAIDiagnostic(datasetId: string): Promise<AIDiagnosticResponse> {
    const id = encodeURIComponent(datasetId);
    return customFetch<AIDiagnosticResponse>(`${API_BASE_URL}/api/ai/diagnose/${id}`, {
      method: "POST",
      body: JSON.stringify({}), // Garante payload JSON válido
    });
  },

  async getDatasetPreview(datasetId: string): Promise<DatasetPreviewResponse> {
    const id = encodeURIComponent(datasetId);
    return customFetch<DatasetPreviewResponse>(`${API_BASE_URL}/api/dataset/${id}/preview`);
  },

  async applyCleaningPipeline(datasetId: string): Promise<TransformationResponse> {
    const id = encodeURIComponent(datasetId);
    return customFetch<TransformationResponse>(`${API_BASE_URL}/api/transformation/apply/${id}`, {
      method: "POST",
      body: JSON.stringify({}), // Garante payload JSON válido
    });
  },

  async exportCSV(datasetId: string): Promise<void> {
    const id = encodeURIComponent(datasetId);
    await downloadBlob(`${API_BASE_URL}/api/export/csv/${id}`, `dataset_limpo_${datasetId}.csv`);
  },

  async exportPDF(datasetId: string): Promise<void> {
    const id = encodeURIComponent(datasetId);
    await downloadBlob(`${API_BASE_URL}/api/export/pdf/${id}`, `relatorio_governanca_${datasetId}.pdf`);
  },

  async getPythonScript(datasetId: string): Promise<string> {
    const id = encodeURIComponent(datasetId);
    const url = `${API_BASE_URL}/api/export/script/${id}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Erro ao carregar o script Python (Status ${res.status})`);
      }
      return await res.text();
    } catch (err: any) {
      clearTimeout(timeoutId);
      throw err;
    }
  },

  async exportScript(datasetId: string): Promise<void> {
    const id = encodeURIComponent(datasetId);
    await downloadBlob(`${API_BASE_URL}/api/export/script/${id}`, `pipeline_${datasetId}.py`);
  },
};