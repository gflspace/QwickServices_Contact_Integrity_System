import React, { useEffect, useState, useCallback } from "react";
import { policyApi, reviewApi, type QueueStats, type ThresholdConfig } from "../api/client";

export default function OpsAnalytics() {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [thresholds, setThresholds] = useState<ThresholdConfig | null>(null);
  const [editingThresholds, setEditingThresholds] = useState(false);
  const [draftThresholds, setDraftThresholds] = useState<ThresholdConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [statsData, thresholdData] = await Promise.all([
        reviewApi.getStats(7),
        policyApi.getThresholds(),
      ]);
      setStats(statsData);
      setThresholds(thresholdData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSaveThresholds = async () => {
    if (!draftThresholds) return;
    try {
      const updated = await policyApi.updateThresholds({
        thresholds: draftThresholds,
        changed_by: "ops-user",
        reason: "Threshold adjustment from ops dashboard",
      });
      setThresholds(updated);
      setEditingThresholds(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update thresholds");
    }
  };

  return (
    <div>
      <h1 style={{ margin: "0 0 20px" }}>Ops Analytics</h1>

      {error && (
        <div style={errorStyle}>{error}</div>
      )}

      {/* Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        <StatCard title="Open Cases" value={stats?.open_cases ?? "—"} color="#e74c3c" />
        <StatCard title="In Review" value={stats?.in_review_cases ?? "—"} color="#f39c12" />
        <StatCard title="Resolved Today" value={stats?.resolved_today ?? "—"} color="#27ae60" />
        <StatCard
          title="False Positive Rate"
          value={stats ? `${(stats.false_positive_rate * 100).toFixed(1)}%` : "—"}
          color="#3498db"
        />
      </div>

      {/* Threshold Configuration */}
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Risk Thresholds</h2>
          {!editingThresholds ? (
            <button
              onClick={() => {
                setDraftThresholds(thresholds);
                setEditingThresholds(true);
              }}
              style={btnStyle}
            >
              Edit Thresholds
            </button>
          ) : (
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={handleSaveThresholds} style={{ ...btnStyle, background: "#27ae60", color: "#fff" }}>
                Save
              </button>
              <button onClick={() => setEditingThresholds(false)} style={btnStyle}>
                Cancel
              </button>
            </div>
          )}
        </div>

        {thresholds && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            <ThresholdRow
              label="Allow (max)"
              value={editingThresholds ? draftThresholds?.allow_max : thresholds.allow_max}
              editing={editingThresholds}
              onChange={(v) => draftThresholds && setDraftThresholds({ ...draftThresholds, allow_max: v })}
              color="#27ae60"
            />
            <ThresholdRow
              label="Nudge (min)"
              value={editingThresholds ? draftThresholds?.nudge_min : thresholds.nudge_min}
              editing={editingThresholds}
              onChange={(v) => draftThresholds && setDraftThresholds({ ...draftThresholds, nudge_min: v })}
              color="#f39c12"
            />
            <ThresholdRow
              label="Nudge (max)"
              value={editingThresholds ? draftThresholds?.nudge_max : thresholds.nudge_max}
              editing={editingThresholds}
              onChange={(v) => draftThresholds && setDraftThresholds({ ...draftThresholds, nudge_max: v })}
              color="#f39c12"
            />
            <ThresholdRow
              label="Soft Block (min)"
              value={editingThresholds ? draftThresholds?.soft_block_min : thresholds.soft_block_min}
              editing={editingThresholds}
              onChange={(v) => draftThresholds && setDraftThresholds({ ...draftThresholds, soft_block_min: v })}
              color="#e67e22"
            />
            <ThresholdRow
              label="Soft Block (max)"
              value={editingThresholds ? draftThresholds?.soft_block_max : thresholds.soft_block_max}
              editing={editingThresholds}
              onChange={(v) => draftThresholds && setDraftThresholds({ ...draftThresholds, soft_block_max: v })}
              color="#e67e22"
            />
            <ThresholdRow
              label="Hard Block (min)"
              value={editingThresholds ? draftThresholds?.hard_block_min : thresholds.hard_block_min}
              editing={editingThresholds}
              onChange={(v) => draftThresholds && setDraftThresholds({ ...draftThresholds, hard_block_min: v })}
              color="#e74c3c"
            />
          </div>
        )}
      </div>

      {/* Risk Band Visualization */}
      <div style={cardStyle}>
        <h2 style={{ margin: "0 0 16px", fontSize: 18 }}>Risk Score Bands</h2>
        {thresholds && (
          <div style={{ display: "flex", height: 40, borderRadius: 4, overflow: "hidden" }}>
            <div style={{ flex: thresholds.allow_max, background: "#27ae60", ...bandStyle }}>
              Allow (0-{thresholds.allow_max})
            </div>
            <div style={{ flex: thresholds.nudge_max - thresholds.nudge_min, background: "#f39c12", ...bandStyle }}>
              Nudge ({thresholds.nudge_min}-{thresholds.nudge_max})
            </div>
            <div
              style={{
                flex: thresholds.soft_block_max - thresholds.soft_block_min,
                background: "#e67e22",
                ...bandStyle,
              }}
            >
              Block ({thresholds.soft_block_min}-{thresholds.soft_block_max})
            </div>
            <div style={{ flex: 1 - thresholds.hard_block_min, background: "#e74c3c", ...bandStyle }}>
              Hard ({thresholds.hard_block_min}+)
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value, color }: { title: string; value: string | number; color: string }) {
  return (
    <div style={{ background: "#fff", borderRadius: 8, padding: 20, borderTop: `3px solid ${color}` }}>
      <div style={{ fontSize: 13, color: "#888", marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function ThresholdRow({
  label,
  value,
  editing,
  onChange,
  color,
}: {
  label: string;
  value: number | undefined;
  editing: boolean;
  onChange: (v: number) => void;
  color: string;
}) {
  return (
    <div style={{ padding: 12, background: "#f9f9f9", borderRadius: 4, borderLeft: `3px solid ${color}` }}>
      <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>{label}</div>
      {editing ? (
        <input
          type="number"
          step="0.01"
          min="0"
          max="1"
          value={value ?? 0}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          style={{ width: "100%", padding: 4, fontSize: 16, border: "1px solid #ddd", borderRadius: 4 }}
        />
      ) : (
        <div style={{ fontSize: 20, fontWeight: 600 }}>{value?.toFixed(2) ?? "—"}</div>
      )}
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 8,
  padding: 20,
  marginBottom: 16,
};
const btnStyle: React.CSSProperties = {
  padding: "8px 16px",
  border: "1px solid #ddd",
  borderRadius: 4,
  background: "#fff",
  cursor: "pointer",
};
const bandStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#fff",
  fontSize: 11,
  fontWeight: 600,
};
const errorStyle: React.CSSProperties = {
  padding: 12,
  background: "#fce4ec",
  borderRadius: 4,
  marginBottom: 16,
  color: "#c62828",
};
