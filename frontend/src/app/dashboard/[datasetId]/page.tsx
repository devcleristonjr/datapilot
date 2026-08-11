"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DataPilotAPI } from "@/lib/api";
import {
  AIDiagnosticResponse,
  DatasetPreviewResponse,
  DatasetProfile,
} from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DashboardCharts } from "@/components/DashboardCharts";
import { toast } from "sonner";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  Download,
  RefreshCw,
  Sparkles,
  Table as TableIcon,
  Wand2,
} from "lucide-react";

export default function DashboardPage() {
  const params = useParams();
  const router = useRouter();

  const rawDatasetId = params?.datasetId;

  const datasetId = Array.isArray(rawDatasetId)
    ? rawDatasetId[0]
    : typeof rawDatasetId === "string"
      ? rawDatasetId
      : undefined;

  const [loading, setLoading] = useState(true);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [cleaning, setCleaning] = useState(false);
  const [exportingCSV, setExportingCSV] = useState(false);
  const [exportingScript, setExportingScript] = useState(false);
  const [isCleaned, setIsCleaned] = useState(false);
  const [copied, setCopied] = useState(false);

  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [diagnostic, setDiagnostic] =
    useState<AIDiagnosticResponse | null>(null);
  const [preview, setPreview] =
    useState<DatasetPreviewResponse | null>(null);

  const [appliedActions, setAppliedActions] = useState<string[]>([]);
  const [pythonScript, setPythonScript] = useState("");

  /*
   * Carrega todos os dados do dashboard.
   */
  const loadDashboardData = useCallback(async () => {
    if (!datasetId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setLoadingError(null);

      const results = await Promise.allSettled([
        DataPilotAPI.getProfile(datasetId),
        DataPilotAPI.getAIDiagnostic(datasetId),
        DataPilotAPI.getDatasetPreview(datasetId),
        DataPilotAPI.getPythonScript(datasetId),
      ]);

      const [profileRes, aiRes, previewRes, scriptRes] = results;

      if (profileRes.status === "fulfilled") {
        setProfile(profileRes.value);
      } else {
        toast.error("Erro ao carregar o perfil do dataset.");
      }

      if (aiRes.status === "fulfilled") {
        setDiagnostic(aiRes.value);
      } else {
        toast.warning("Diagnóstico de IA temporariamente indisponível.");
      }

      if (previewRes.status === "fulfilled") {
        setPreview(previewRes.value);
      } else {
        toast.error("Erro ao carregar a pré-visualização dos dados.");
      }

      if (scriptRes.status === "fulfilled") {
        setPythonScript(scriptRes.value);
      }

      const hasAnyFailure = results.some((result) => result.status === "rejected");
      if (hasAnyFailure) {
        setLoadingError("Alguns módulos do dashboard não puderam ser carregados. Tente novamente.");
      }
    } catch (error: any) {
      const message = error?.message || "Erro inesperado ao carregar o dashboard.";
      setLoadingError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  /*
   * Limpeza automática.
   */
  const handleApplyCleaning = async () => {
    if (!datasetId) return;

    try {
      setCleaning(true);

      toast.loading(
        "Executando pipeline de limpeza em Pandas...",
        {
          id: "clean-toast",
        }
      );

      const result =
        await DataPilotAPI.applyCleaningPipeline(datasetId);

      setAppliedActions(result.applied_actions || []);
      setIsCleaned(true);

      const [
        updatedProfile,
        updatedPreview,
        updatedDiagnostic,
        updatedScript,
      ] = await Promise.allSettled([
        DataPilotAPI.getProfile(datasetId),
        DataPilotAPI.getDatasetPreview(datasetId),
        DataPilotAPI.getAIDiagnostic(datasetId),
        DataPilotAPI.getPythonScript(datasetId),
      ]);

      if (updatedProfile.status === "fulfilled") {
        setProfile(updatedProfile.value);
      }

      if (updatedPreview.status === "fulfilled") {
        setPreview(updatedPreview.value);
      }

      if (updatedDiagnostic.status === "fulfilled") {
        setDiagnostic(updatedDiagnostic.value);
      }

      if (updatedScript.status === "fulfilled") {
        setPythonScript(updatedScript.value);
      }

      toast.success("Tratamento concluído com sucesso!", {
        id: "clean-toast",
      });
    } catch (error: any) {
      toast.error(
        `Erro ao aplicar limpeza: ${
          error?.message || "Falha na execução"
        }`,
        {
          id: "clean-toast",
        }
      );
    } finally {
      setCleaning(false);
    }
  };

  /*
   * Exportar CSV.
   */
  const handleExportCSV = async () => {
    if (!datasetId) return;

    try {
      setExportingCSV(true);

      await DataPilotAPI.exportCSV(datasetId);

      toast.success("Download do CSV iniciado com sucesso!");
    } catch (error: any) {
      toast.error(
        `Erro ao exportar CSV: ${
          error?.message || "Falha no download"
        }`
      );
    } finally {
      setExportingCSV(false);
    }
  };

  /*
   * Download do script Python.
   */
  const handleDownloadScript = async () => {
    if (!datasetId) return;

    try {
      setExportingScript(true);

      await DataPilotAPI.exportScript(datasetId);

      toast.success("Download do arquivo .py iniciado!");
    } catch (error: any) {
      toast.error(
        `Erro ao baixar script Python: ${
          error?.message || "Falha no download"
        }`
      );
    } finally {
      setExportingScript(false);
    }
  };

  /*
   * Copiar código Python.
   */
  const handleCopyScript = async () => {
    if (!pythonScript) return;

    try {
      await navigator.clipboard.writeText(pythonScript);

      setCopied(true);

      toast.success(
        "Código Python copiado para a área de transferência!"
      );

      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch {
      toast.error("Não foi possível copiar o código.");
    }
  };

  /*
   * Dataset inexistente na URL.
   *
   * Isso evita o problema original de loading infinito.
   */
  if (!datasetId) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
        <Card className="w-full max-w-lg bg-slate-900 border-slate-800 text-slate-100">
          <CardHeader>
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 text-amber-400" />

              <CardTitle>
                Dataset não informado
              </CardTitle>
            </div>
          </CardHeader>

          <CardContent className="space-y-5">
            <p className="text-sm leading-6 text-slate-400">
              Não foi possível identificar a planilha que deve ser
              analisada. Volte para a página inicial e envie um
              arquivo novamente.
            </p>

            <Button
              onClick={() => router.push("/")}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Voltar para o início
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  /*
   * Loading.
   */
  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-4">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />

        <div className="text-center">
          <p className="text-sm text-slate-300">
            Processando planilha...
          </p>

          <p className="mt-1 text-xs text-slate-600">
            Gerando perfil, diagnóstico e pré-visualização
          </p>
        </div>
      </main>
    );
  }

  if (loadingError) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
        <Card className="w-full max-w-lg border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader>
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 text-amber-400" />
              <CardTitle>Não foi possível carregar o dashboard</CardTitle>
            </div>
          </CardHeader>

          <CardContent className="space-y-5">
            <p className="text-sm leading-6 text-slate-400">{loadingError}</p>

            <div className="flex gap-3">
              <Button onClick={() => loadDashboardData()} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Tentar novamente
              </Button>

              <Button variant="outline" onClick={() => router.push("/")} className="border-slate-700 text-slate-200 hover:bg-slate-800">
                Voltar ao início
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10">
      <div className="mx-auto max-w-[1600px] space-y-8">

        {/* Cabeçalho */}
        <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-center md:justify-between">
          <div>
            <button
              type="button"
              onClick={() => router.push("/")}
              className="mb-4 inline-flex items-center gap-2 text-xs text-slate-500 transition-colors hover:text-slate-200"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Nova análise
            </button>

            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight md:text-3xl">
                Painel de Governança
              </h1>

              {isCleaned ? (
                <span className="flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Base Higienizada
                </span>
              ) : (
                <span className="flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-400">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Dados Brutos
                </span>
              )}
            </div>

            <p className="mt-1 text-sm text-slate-500">
              Dataset ID:{" "}
              <span className="font-mono text-slate-400">
                {datasetId}
              </span>
            </p>
          </div>

          {/* Ações */}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={handleApplyCleaning}
              disabled={cleaning}
              className="gap-2 bg-blue-600 text-white hover:bg-blue-500"
            >
              {cleaning ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4" />
              )}

              {cleaning
                ? "Aplicando..."
                : "Executar Limpeza Automática"}
            </Button>

            <Button
              variant="outline"
              onClick={handleExportCSV}
              disabled={exportingCSV}
              className="gap-2 border-slate-800 text-slate-200 hover:bg-slate-900"
            >
              {exportingCSV ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}

              {exportingCSV
                ? "Exportando..."
                : "Exportar CSV"}
            </Button>
          </div>
        </header>

        {/* Métricas */}
        {profile && (
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Total de Linhas"
              value={profile.total_rows?.toLocaleString() ?? "0"}
            />

            <MetricCard
              title="Total de Colunas"
              value={profile.total_columns ?? "0"}
            />

            <MetricCard
              title="Linhas Duplicadas"
              value={profile.duplicate_rows_count ?? "0"}
              valueClass={
                (profile.duplicate_rows_count ?? 0) > 0
                  ? "text-amber-400"
                  : "text-emerald-400"
              }
            />

            <MetricCard
              title="Score da IA"
              value={
                diagnostic?.quality_score !== undefined
                  ? `${diagnostic.quality_score} / 100`
                  : "N/A"
              }
              valueClass="text-blue-400"
            />
          </section>
        )}

        {/* Diagnóstico IA */}
        {diagnostic && (
          <Card className="border-slate-800 bg-slate-900 text-slate-100">
            <CardHeader className="flex flex-row items-center gap-2 border-b border-slate-800/60 pb-4">
              <Sparkles className="h-5 w-5 text-blue-400" />

              <CardTitle className="text-lg">
                Diagnóstico do Motor Gemini
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-5 pt-5">
              <p className="text-sm leading-6 text-slate-300 md:text-base">
                {diagnostic.executive_summary}
              </p>

              {diagnostic.health_status && (
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Status da Base
                  </span>

                  <p className="mt-1 text-sm text-slate-300">
                    {diagnostic.health_status}
                  </p>
                </div>
              )}

              {diagnostic.key_findings?.length > 0 && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Principais Achados
                  </h4>

                  <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
                    {diagnostic.key_findings.map(
                      (finding, index) => (
                        <li key={`finding-${index}`}>
                          {finding}
                        </li>
                      )
                    )}
                  </ul>
                </div>
              )}

              {diagnostic.issues?.length > 0 && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber-400">
                    Problemas Identificados
                  </h4>

                  <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
                    {diagnostic.issues.map(
                      (issue, index) => (
                        <li key={`issue-${index}`}>
                          {issue}
                        </li>
                      )
                    )}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Ações de limpeza */}
        {appliedActions.length > 0 && (
          <Card className="border-emerald-800/40 bg-emerald-950/20 text-slate-100">
            <CardHeader className="flex flex-row items-center gap-2 pb-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />

              <CardTitle className="text-base font-semibold text-emerald-300">
                Ações de Limpeza Executadas pelo Pandas
              </CardTitle>
            </CardHeader>

            <CardContent>
              <ul className="space-y-2 text-sm text-emerald-200/90">
                {appliedActions.map((action, index) => (
                  <li
                    key={`action-${index}`}
                    className="flex items-start gap-2"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />

                    {action}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Gráficos */}
        {profile && (
          <DashboardCharts profile={profile} />
        )}

        {/* Script Python */}
        {pythonScript && (
          <Card className="border-slate-800 bg-slate-900 text-slate-100">
            <CardHeader className="flex flex-col gap-4 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <Code2 className="h-5 w-5 text-blue-400" />

                <div>
                  <CardTitle className="text-base font-semibold">
                    Script Python para Reprodutibilidade
                  </CardTitle>

                  <p className="text-xs text-slate-500">
                    Código Pandas automatizado gerado para este dataset
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyScript}
                  className="gap-1.5 border-slate-700 text-xs text-slate-300 hover:bg-slate-800"
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}

                  {copied ? "Copiado!" : "Copiar Código"}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadScript}
                  disabled={exportingScript}
                  className="gap-1.5 border-slate-700 text-xs text-slate-300 hover:bg-slate-800"
                >
                  {exportingScript ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5" />
                  )}

                  {exportingScript
                    ? "Baixando..."
                    : "Baixar .py"}
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <pre className="max-h-96 overflow-x-auto bg-slate-950 p-4 font-mono text-xs leading-relaxed text-blue-300/90">
                <code>{pythonScript}</code>
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Preview */}
        {preview?.columns && (
          <Card className="border-slate-800 bg-slate-900 text-slate-100">
            <CardHeader className="flex flex-row items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2">
                <TableIcon className="h-5 w-5 text-slate-400" />

                <CardTitle className="text-base font-semibold">
                  Preview dos Dados
                </CardTitle>
              </div>

              <span className="text-xs text-slate-500">
                {preview.rows?.length || 0} registros exibidos
              </span>
            </CardHeader>

            <CardContent className="overflow-x-auto p-0">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="border-b border-slate-800 bg-slate-950 text-slate-400">
                  <tr>
                    {preview.columns.map((column, index) => (
                      <th
                        key={`column-${index}-${column}`}
                        className="whitespace-nowrap px-4 py-3 font-medium uppercase tracking-wider"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-800/60">
                  {(preview.rows || []).map(
                    (row, rowIndex) => (
                      <tr
                        key={`row-${rowIndex}`}
                        className="transition-colors hover:bg-slate-800/40"
                      >
                        {preview.columns.map(
                          (column, columnIndex) => {
                            const value = row[column];

                            return (
                              <td
                                key={`cell-${rowIndex}-${columnIndex}`}
                                className="whitespace-nowrap px-4 py-2.5 text-slate-300"
                              >
                                {value !== null &&
                                value !== undefined ? (
                                  String(value)
                                ) : (
                                  <span className="italic text-slate-600">
                                    null
                                  </span>
                                )}
                              </td>
                            );
                          }
                        )}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}

function MetricCard({
  title,
  value,
  valueClass = "",
}: {
  title: string;
  value: string | number;
  valueClass?: string;
}) {
  return (
    <Card className="border-slate-800 bg-slate-900 text-slate-100">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {title}
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className={`text-2xl font-bold ${valueClass}`}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}