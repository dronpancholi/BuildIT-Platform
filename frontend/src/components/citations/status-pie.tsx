"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface StatusBreakdown {
  status: string;
  count: number;
  percentage: number;
}

interface StatusPieProps {
  data: StatusBreakdown[];
  height?: number;
}

const STATUS_COLORS: Record<string, string> = {
  completed: "#10b981",
  verified: "#10b981",
  live: "#10b981",
  in_progress: "#3b82f6",
  pending: "#f59e0b",
  pending_review: "#f59e0b",
  not_started: "#64748b",
  already_exists: "#8b5cf6",
  new_backlink: "#06b6d4",
  failed: "#ef4444",
  rejected: "#ef4444",
};

const DEFAULT_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

export function StatusPie({ data, height = 250 }: StatusPieProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-slate-500 text-sm"
        style={{ height }}
      >
        No status data available yet
      </div>
    );
  }

  const chartData = data.filter((d) => d.count > 0);

  if (chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-slate-500 text-sm"
        style={{ height }}
      >
        No submissions yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="count"
          nameKey="status"
        >
          {chartData.map((entry, index) => (
            <Cell
              key={entry.status}
              fill={
                STATUS_COLORS[entry.status] ||
                DEFAULT_COLORS[index % DEFAULT_COLORS.length]
              }
              stroke="transparent"
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          formatter={(value: any, name: any) => [
            value,
            name.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
          ]}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value: string) =>
            value
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())
          }
          wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
