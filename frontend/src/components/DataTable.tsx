"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, ChevronLeft, ChevronRight, Table as TableIcon } from "lucide-react";

interface DataTableProps {
  columns: string[];
  rows: Record<string, any>[];
}

export function DataTable({ columns, rows }: DataTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  // Filtra linhas baseando-se no termo buscado
  const filteredRows = rows.filter((row) =>
    columns.some((col) => {
      const val = row[col];
      return val !== null && val !== undefined && String(val).toLowerCase().includes(searchTerm.toLowerCase());
    })
  );

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage) || 1;
  const startIndex = (currentPage - 1) * rowsPerPage;
  const currentRows = filteredRows.slice(startIndex, startIndex + rowsPerPage);

  // Identifica células vazias ou não informadas para destaque
  const isValueEmpty = (val: any) => {
    return (
      val === null ||
      val === undefined ||
      val === "" ||
      val === "Não informado" ||
      val === "nan" ||
      val === "NaN"
    );
  };

  return (
    <Card className="bg-slate-900/90 border-slate-800 shadow-xl">
      <CardHeader className="border-b border-slate-800/80 p-4 md:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <TableIcon className="w-5 h-5 text-blue-400" />
          <CardTitle className="text-lg font-semibold text-slate-100">
            Visualização e Estrutura dos Dados
          </CardTitle>
          <span className="text-xs bg-slate-800 text-slate-400 px-2.5 py-1 rounded-full border border-slate-700">
            {rows.length} registros
          </span>
        </div>

        {/* Campo de Busca */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            type="text"
            placeholder="Buscar na tabela..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="pl-9 bg-slate-950 border-slate-800 text-slate-200 placeholder:text-slate-500 focus:border-blue-500 text-sm"
          />
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/80 text-xs uppercase text-slate-400 border-b border-slate-800 tracking-wider">
              <tr>
                <th className="px-4 py-3 w-12 text-center text-slate-600">#</th>
                {columns.map((col) => (
                  <th key={col} className="px-4 py-3 font-semibold text-slate-200 whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {currentRows.length > 0 ? (
                currentRows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 text-center text-xs text-slate-500 font-mono">
                      {startIndex + idx + 1}
                    </td>
                    {columns.map((col) => {
                      const val = row[col];
                      const isEmpty = isValueEmpty(val);

                      return (
                        <td key={col} className="px-4 py-3 whitespace-nowrap">
                          {isEmpty ? (
                            <span className="inline-block px-2 py-0.5 rounded text-xs bg-yellow-950/40 border border-yellow-800/50 text-yellow-500 italic">
                              {val === "Não informado" ? "Não informado" : "Ausente"}
                            </span>
                          ) : typeof val === "number" ? (
                            <span className="font-mono text-slate-200">
                              {val.toLocaleString("pt-BR")}
                            </span>
                          ) : (
                            String(val)
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={columns.length + 1} className="text-center py-8 text-slate-500">
                    Nenhum registro encontrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Paginador */}
        <div className="flex items-center justify-between p-4 border-t border-slate-800/80 text-xs text-slate-400">
          <div>
            Exibindo <span className="font-medium text-slate-200">{filteredRows.length > 0 ? startIndex + 1 : 0}</span> a{" "}
            <span className="font-medium text-slate-200">
              {Math.min(startIndex + rowsPerPage, filteredRows.length)}
            </span>{" "}
            de <span className="font-medium text-slate-200">{filteredRows.length}</span> resultados
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              className="h-8 border-slate-800 bg-slate-950 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
            </Button>
            <span className="px-2">
              Página {currentPage} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
              className="h-8 border-slate-800 bg-slate-950 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
            >
              Próxima <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}