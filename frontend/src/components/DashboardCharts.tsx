"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatasetProfile } from "@/types/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

interface DashboardChartsProps {
  profile: DatasetProfile;
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export function DashboardCharts({ profile }: DashboardChartsProps) {
  // Gráfico 1: Top colunas com mais valores nulos
  const nullData = profile.columns_profile
    .map((col) => ({
      name: col.name.length > 12 ? `${col.name.slice(0, 10)}...` : col.name,
      nulos: col.null_count,
    }))
    .filter((col) => col.nulos > 0)
    .sort((a, b) => b.nulos - a.nulos)
    .slice(0, 6);

  // Gráfico 2: Distribuição dos tipos de dados nas colunas
  const typeCounts: Record<string, number> = {};
  profile.columns_profile.forEach((col) => {
    const type = col.inferred_type.includes("int") || col.inferred_type.includes("float")
      ? "Numérico"
      : col.inferred_type.includes("datetime")
      ? "Data"
      : "Texto";
    typeCounts[type] = (typeCounts[type] || 0) + 1;
  });

  const typeData = Object.keys(typeCounts).map((key) => ({
    name: key,
    value: typeCounts[key],
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 my-6">
      {/* Gráfico de Distribuição de Tipos */}
      <Card className="bg-slate-900 border-slate-800 text-slate-100">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Distribuição dos Tipos de Colunas</CardTitle>
        </CardHeader>
        <CardContent className="h-64 flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={typeData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              >
                {typeData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", color: "#f8fafc" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Gráfico de Valores Nulos por Coluna */}
      <Card className="bg-slate-900 border-slate-800 text-slate-100">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Inconsistências / Nulos por Coluna</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          {nullData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={nullData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", color: "#f8fafc" }}
                />
                <Bar dataKey="nulos" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">
              Nenhuma coluna com valores ausentes encontrada!
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}