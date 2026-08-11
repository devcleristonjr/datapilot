"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { DataPilotAPI, type DatasetHistoryEntry } from "@/lib/api";
import { toast } from "sonner";
import {
  Upload,
  FileSpreadsheet,
  Sparkles,
  ShieldCheck,
  BarChart3,
  ArrowRight,
  RefreshCw,
  X,
} from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [recentDatasets, setRecentDatasets] = useState<DatasetHistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        setLoadingHistory(true);
        const datasets = await DataPilotAPI.getDatasetHistory();
        setRecentDatasets(datasets.slice(0, 5));
      } catch {
        setRecentDatasets([]);
      } finally {
        setLoadingHistory(false);
      }
    };

    loadHistory();
  }, []);

  const acceptedTypes = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "application/csv",
  ];

  const validateFile = (selectedFile: File): boolean => {
    const extension = selectedFile.name.toLowerCase().split(".").pop();

    if (!["xlsx", "xls", "csv"].includes(extension || "")) {
      toast.error("Formato não suportado. Envie um arquivo Excel ou CSV.");
      return false;
    }

    return true;
  };

  const selectFile = (selectedFile: File) => {
    if (!validateFile(selectedFile)) {
      return;
    }

    setFile(selectedFile);
  };

  const triggerFilePicker = () => {
    if (uploading) {
      return;
    }
    fileInputRef.current?.click();
  };

  const handleUploadAreaClick = () => {
    if (!file && !uploading) {
      triggerFilePicker();
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];

    if (selectedFile) {
      selectFile(selectedFile);
    }

    event.target.value = "";
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {
      selectFile(droppedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      toast.error("Selecione uma planilha primeiro.");
      return;
    }

    try {
      setUploading(true);

      toast.loading("Enviando planilha para o DataPilot...", {
        id: "upload-toast",
      });

      const result = await DataPilotAPI.uploadFile(file);

      toast.success("Planilha carregada com sucesso!", {
        id: "upload-toast",
      });

      /*
       * O backend gera um dataset_id único.
       * Agora navegamos para:
       *
       * /dashboard/{dataset_id}
       */
      router.push(`/dashboard/${result.dataset_id}`);
    } catch (error: any) {
      toast.error(
        error?.message ||
          "Não foi possível processar a planilha. Verifique se o backend está ativo.",
        {
          id: "upload-toast",
        }
      );
    } finally {
      setUploading(false);
    }
  };

  const removeFile = () => {
    setFile(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute left-1/2 top-[-300px] h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-blue-600/10 blur-3xl" />
        <div className="absolute bottom-[-300px] left-[-200px] h-[500px] w-[500px] rounded-full bg-indigo-600/10 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-10">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600">
              <Sparkles className="h-5 w-5 text-white" />
            </div>

            <div>
              <h1 className="text-lg font-bold tracking-tight">
                DataPilot <span className="text-blue-400">IA</span>
              </h1>

              <p className="text-xs text-slate-500">
                Governança inteligente de dados
              </p>
            </div>
          </div>

          <div className="hidden items-center gap-2 text-xs text-slate-500 sm:flex">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            Processamento seguro
          </div>
        </header>

        {/* Hero */}
        <section className="flex flex-1 flex-col items-center justify-center py-16">
          <div className="mb-10 max-w-2xl text-center">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-400">
              <Sparkles className="h-3.5 w-3.5" />
              Análise inteligente de planilhas
            </div>

            <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Transforme sua planilha em{" "}
              <span className="text-blue-500">informação útil.</span>
            </h2>

            <p className="mx-auto mt-5 max-w-xl text-sm leading-6 text-slate-400 sm:text-base">
              Envie sua planilha e deixe o DataPilot analisar a qualidade dos
              dados, identificar inconsistências, encontrar duplicidades e
              gerar um diagnóstico automático.
            </p>
          </div>

          {/* Upload */}
          <div className="w-full max-w-2xl">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={handleUploadAreaClick}
              className={`
                group relative cursor-pointer rounded-2xl border-2 border-dashed
                p-10 text-center transition-all duration-200
                ${
                  dragActive
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900"
                }
                ${uploading ? "pointer-events-none opacity-70" : ""}
              `}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                aria-label="Selecionar planilha"
                className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                onChange={handleFileChange}
              />

              {!file ? (
                <>
                  <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-400 transition-transform group-hover:scale-105">
                    <Upload className="h-7 w-7" />
                  </div>

                  <h3 className="text-lg font-semibold">
                    Arraste sua planilha aqui
                  </h3>

                  <p className="mt-2 text-sm text-slate-500">
                    ou clique para selecionar um arquivo
                  </p>

                  <div className="mt-5 flex justify-center gap-2">
                    <span className="rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-500">
                      XLSX
                    </span>

                    <span className="rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-500">
                      XLS
                    </span>

                    <span className="rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-500">
                      CSV
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      triggerFilePicker();
                    }}
                    className="mt-5 inline-flex items-center justify-center rounded-xl border border-blue-500/40 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-300 transition-colors hover:bg-blue-500/20"
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    Selecionar arquivo
                  </button>
                </>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400">
                    <FileSpreadsheet className="h-8 w-8" />
                  </div>

                  <h3 className="max-w-full truncate px-4 text-lg font-semibold">
                    {file.name}
                  </h3>

                  <p className="mt-2 text-sm text-slate-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      removeFile();
                    }}
                    className="mt-4 inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs text-slate-500 transition-colors hover:bg-slate-800 hover:text-slate-200"
                  >
                    <X className="h-3.5 w-3.5" />
                    Remover arquivo
                  </button>
                </div>
              )}
            </div>

            {/* Upload Button */}
            <button
              type="button"
              onClick={handleUpload}
              disabled={!file || uploading}
              className="mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {uploading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Processando planilha...
                </>
              ) : (
                <>
                  Analisar planilha
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>

          <div className="mt-10 w-full max-w-3xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">
                Histórico recente
              </h3>
              <span className="text-xs text-slate-500">
                {loadingHistory ? "Carregando..." : `${recentDatasets.length} itens`}
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {recentDatasets.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-400 sm:col-span-2">
                  Ainda não há datasets salvos. Faça o primeiro upload para começar.
                </div>
              ) : (
                recentDatasets.map((dataset) => (
                  <button
                    key={dataset.dataset_id}
                    type="button"
                    onClick={() => router.push(`/dashboard/${dataset.dataset_id}`)}
                    className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-left transition-colors hover:border-blue-500/40 hover:bg-slate-900"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-100">
                          {dataset.filename}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {dataset.rows_count} linhas · {dataset.columns_count} colunas
                        </p>
                      </div>
                      <ArrowRight className="h-4 w-4 shrink-0 text-blue-400" />
                    </div>
                    <p className="mt-3 text-[11px] text-slate-500">
                      Atualizado {dataset.updated_at ? new Date(dataset.updated_at).toLocaleString("pt-BR") : "recentemente"}
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Features */}
          <div className="mt-14 grid w-full max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
            <Feature
              icon={<BarChart3 className="h-5 w-5" />}
              title="Perfil dos dados"
              description="Linhas, colunas, nulos e duplicidades."
            />

            <Feature
              icon={<Sparkles className="h-5 w-5" />}
              title="Diagnóstico com IA"
              description="Análise automática da qualidade da base."
            />

            <Feature
              icon={<ShieldCheck className="h-5 w-5" />}
              title="Higienização"
              description="Pipeline automático usando Pandas."
            />
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-slate-900 pt-6 text-center text-xs text-slate-600">
          DataPilot IA • Análise e Governança Automática de Dados
        </footer>
      </div>
    </main>
  );
}

function Feature({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-slate-900 bg-slate-950/50 p-5">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
        {icon}
      </div>

      <h3 className="text-sm font-semibold">{title}</h3>

      <p className="mt-1 text-xs leading-5 text-slate-500">
        {description}
      </p>
    </div>
  );
}