"use client";

import React, { useState, useRef } from "react";
import { Upload, FileSpreadsheet, Loader2 } from "lucide-react";
import { DataPilotAPI } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface UploadZoneProps {
  onUploadSuccess: (datasetId: string) => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = async (file: File) => {
    if (!file.name.match(/\.(csv|xlsx|xls)$/i)) {
      setErrorMsg("Formato inválido. Por favor, envie um arquivo CSV ou Excel (.xlsx).");
      return;
    }

    setErrorMsg(null);
    setIsUploading(true);

    try {
      const response = await DataPilotAPI.uploadFile(file);
      onUploadSuccess(response.dataset_id);
    } catch (err: any) {
      console.error("Erro no upload:", err);
      if (err?.code === "ERR_NETWORK") {
        setErrorMsg("Não foi possível conectar ao servidor backend (http://localhost:8000). Verifique se o FastAPI está rodando.");
      } else {
        setErrorMsg(err?.response?.data?.detail || "Erro ao realizar o upload da base.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleButtonClick = () => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto border-2 border-dashed border-slate-700 bg-slate-900/50">
      <CardContent
        className={`relative p-8 text-center transition-colors ${
          dragActive ? "border-blue-500 bg-blue-500/10" : ""
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="p-4 bg-blue-500/10 text-blue-400 rounded-full">
            {isUploading ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : (
              <FileSpreadsheet className="w-8 h-8" />
            )}
          </div>

          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-slate-100">
              {isUploading ? "Convertendo e Analisando Base..." : "Arraste sua planilha aqui"}
            </h3>
            <p className="text-sm text-slate-400">
              Suporta arquivos CSV e Excel (.xlsx) até 100MB
            </p>
          </div>

          {!isUploading && (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                accept=".csv, .xlsx, .xls"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleFile(e.target.files[0]);
                  }
                  e.target.value = "";
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleButtonClick}
                className="mt-2"
              >
                <Upload className="w-4 h-4 mr-2" /> Selecionar Arquivo
              </Button>
            </div>
          )}

          {errorMsg && (
            <p className="text-sm text-red-400 font-medium mt-2 max-w-md mx-auto">{errorMsg}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
