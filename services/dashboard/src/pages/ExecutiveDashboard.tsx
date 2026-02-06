import React, { useEffect, useState, useCallback } from "react";
import { reviewApi, type QueueStats } from "../api/client";

export default function ExecutiveDashboard() {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [period, setPeriod] = useState(7);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await reviewApi.getStats(period);
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    }
  }, [period]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const totalCases = stats
    ? stats.open_cases + stats.in_review_cases + stats.resolved_today
    : 0;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>Executive Dashboard</h1>
        <select
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          style={{ padding: "8px 12px", borderRadius: 4, border: "1px solid #ddd" }}
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fce4ec", borderRadius: 4, marginBottom: 16, color: "#c62828" }}>
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        <KPICard
          title="Total Cases"
          value={totalCases}
          subtitle="All integrity cases"
          trend={null}
        />
        <KPICard
          title="Resolution Rate"
          value={
            totalCases > 0
              ? `${((stats?.resolved_today ?? 0) / totalCases * 100).toFixed(0)}%`
              : "—"
          }
          subtitle="Cases resolved"
          trend={null}
        />
        <KPICard
          title="Avg Resolution"
          value={stats ? `${stats.avg_resolution_hours.toFixed(1)}h` : "—"}
          subtitle="Hours to resolve"
          trend={null}
        />
        <KPICard
          title="False Positive Rate"
          value={stats ? `${(stats.false_positive_rate * 100).toFixed(1)}%` : "—"}
          subtitle="Incorrectly flagged"
          trend={null}
        />
      </div>

      {/* Case Distribution */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={cardStyle}>
          <h2 style={{ margin: "0 0 16px", fontSize: 18 }}>Case Status Breakdown</h2>
          {stats && (
            <div>
              <StatusBar label="Open" value={stats.open_cases} total={totalCases} color="#e74c3c" />
              <StatusBar label="In Review" value={stats.in_review_cases} total={totalCases} color="#f39c12" />
              <StatusBar label="Resolved" value={stats.resolved_today} total={totalCases} color="#27ae60" />
            </div>
          )}
        </div>

        <div style={cardStyle}>
          <h2 style={{ margin: "0 0 16px", fontSize: 18 }}>Top Detection Labels</h2>
          {stats && stats.top_labels.length > 0 ? (
            <div>
              {stats.top_labels.map((item, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f0f0f0" }}>
                  <span style={{ fontSize: 14 }}>{item.label}</span>
                  <span style={{ fontWeight: 600 }}>{item.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "#999" }}>No label data available</p>
          )}
        </div>
      </div>

      {/* Platform Health */}
      <div style={{ ...cardStyle, marginTop: 16 }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 18 }}>System Health</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
          <ServiceStatus name="Interceptor" status="healthy" />
          <ServiceStatus name="Detection" status="healthy" />
          <ServiceStatus name="Policy" status="healthy" />
          <ServiceStatus name="Review" status="healthy" />
          <ServiceStatus name="Database" status="healthy" />
        </div>
      </div>
    </div>
  );
}

function KPICard({
  title,
  value,
  subtitle,
  trend,
}: {
  title: string;
  value: string | number;
  subtitle: string;
  trend: number | null;
}) {
  return (
    <div style={{ background: "#fff", borderRadius: 8, padding: 20 }}>
      <div style={{ fontSize: 13, color: "#888", marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color: "#1a1a2e", marginBottom: 4 }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: "#aaa" }}>
        {subtitle}
        {trend !== null && (
          <span style={{ marginLeft: 8, color: trend >= 0 ? "#27ae60" : "#e74c3c" }}>
            {trend >= 0 ? "+" : ""}{trend}%
          </span>
        )}
      </div>
    </div>
  );
}

function StatusBar({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ fontWeight: 600 }}>{value}</span>
      </div>
      <div style={{ height: 8, background: "#f0f0f0", borderRadius: 4 }}>
        <div style={{ height: 8, width: `${pct}%`, background: color, borderRadius: 4 }} />
      </div>
    </div>
  );
}

function ServiceStatus({ name, status }: { name: string; status: string }) {
  const color = status === "healthy" ? "#27ae60" : status === "degraded" ? "#f39c12" : "#e74c3c";
  return (
    <div style={{ textAlign: "center", padding: 12, background: "#f9f9f9", borderRadius: 4 }}>
      <div
        style={{
          width: 12,
          height: 12,
          borderRadius: "50%",
          background: color,
          margin: "0 auto 8px",
        }}
      />
      <div style={{ fontSize: 13, fontWeight: 600 }}>{name}</div>
      <div style={{ fontSize: 11, color: "#888" }}>{status}</div>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 8,
  padding: 20,
};
