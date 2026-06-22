"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface GrowthData {
  date: string;
  total: number;
  verified: number;
  pending: number;
  failed: number;
}

interface GrowthChartProps {
  data: GrowthData[];
  height?: number;
}

export function GrowthChart({ data, height = 300 }: GrowthChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-slate-500 text-sm"
        style={{ height }}
      >
        No growth data available yet
      </div>
    );
  }

  const formattedData = data.map((d) => ({
    ...d,
    displayDate: new Date(d.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={formattedData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="displayDate"
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={{ stroke: "#475569" }}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={{ stroke: "#475569" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          labelStyle={{ color: "#e2e8f0" }}
        />
        <Line
          type="monotone"
          dataKey="total"
          stroke="#6366f1"
          strokeWidth={2}
          dot={false}
          name="Total"
        />
        <Line
          type="monotone"
          dataKey="verified"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
          name="Verified"
        />
        <Line
          type="monotone"
          dataKey="pending"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
          name="Pending"
        />
        <Line
          type="monotone"
          dataKey="failed"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
          name="Failed"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
