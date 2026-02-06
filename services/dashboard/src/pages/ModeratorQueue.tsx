import React, { useEffect, useState, useCallback } from "react";
import { reviewApi, type Case } from "../api/client";

type StatusFilter = "open" | "in_review" | "all";

const STATUS_COLORS: Record<string, string> = {
  open: "#e74c3c",
  in_review: "#f39c12",
  resolved: "#27ae60",
  appealed: "#8e44ad",
  overturned: "#95a5a6",
};

export default function ModeratorQueue() {
  const [cases, setCases] = useState<Case[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<StatusFilter>("open");
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { status?: string; limit: number } = { limit: 50 };
      if (filter !== "all") params.status = filter;
      const response = await reviewApi.listCases(params);
      setCases(response.cases);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const handleAssign = async (caseId: string, moderatorId: string) => {
    try {
      await reviewApi.updateCase(caseId, { assigned_to: moderatorId });
      loadCases();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign case");
    }
  };

  const handleResolve = async (
    caseId: string,
    resolution: "confirmed" | "false_positive" | "escalated"
  ) => {
    try {
      await reviewApi.updateCase(caseId, {
        status: "resolved",
        resolution,
      });
      setSelectedCase(null);
      loadCases();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve case");
    }
  };

  return (
    <div>
      <h1 style={{ margin: "0 0 20px" }}>Moderator Queue</h1>

      {/* Filters */}
      <div style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        {(["open", "in_review", "all"] as StatusFilter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "8px 16px",
              border: "1px solid #ddd",
              borderRadius: 4,
              background: filter === f ? "#3498db" : "#fff",
              color: filter === f ? "#fff" : "#333",
              cursor: "pointer",
            }}
          >
            {f === "all" ? "All" : f.replace("_", " ").toUpperCase()}
          </button>
        ))}
        <span style={{ marginLeft: "auto", color: "#888" }}>
          {total} case{total !== 1 ? "s" : ""}
        </span>
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fce4ec", borderRadius: 4, marginBottom: 16, color: "#c62828" }}>
          {error}
        </div>
      )}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <div style={{ display: "flex", gap: 20 }}>
          {/* Case List */}
          <div style={{ flex: 1 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: 8 }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #eee", textAlign: "left" }}>
                  <th style={thStyle}>Priority</th>
                  <th style={thStyle}>User</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Assigned</th>
                  <th style={thStyle}>Created</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => setSelectedCase(c)}
                    style={{
                      borderBottom: "1px solid #f0f0f0",
                      cursor: "pointer",
                      background: selectedCase?.id === c.id ? "#e3f2fd" : "transparent",
                    }}
                  >
                    <td style={tdStyle}>
                      <span style={{
                        display: "inline-block",
                        width: 24, height: 24,
                        borderRadius: "50%",
                        background: c.priority >= 5 ? "#e74c3c" : c.priority >= 3 ? "#f39c12" : "#95a5a6",
                        color: "#fff",
                        textAlign: "center",
                        lineHeight: "24px",
                        fontSize: 12,
                      }}>
                        {c.priority}
                      </span>
                    </td>
                    <td style={tdStyle}>{c.user_id}</td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: 12,
                        background: STATUS_COLORS[c.status] || "#999",
                        color: "#fff",
                      }}>
                        {c.status}
                      </span>
                    </td>
                    <td style={tdStyle}>{c.assigned_to || "—"}</td>
                    <td style={tdStyle}>{new Date(c.created_at).toLocaleDateString()}</td>
                    <td style={tdStyle}>
                      {c.status === "open" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAssign(c.id, "current-moderator");
                          }}
                          style={btnStyle}
                        >
                          Claim
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {cases.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ ...tdStyle, textAlign: "center", color: "#999" }}>
                      No cases found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Case Detail Panel */}
          {selectedCase && (
            <div style={{ width: 350, background: "#fff", borderRadius: 8, padding: 20 }}>
              <h3 style={{ margin: "0 0 16px" }}>Case Detail</h3>
              <dl style={{ margin: 0, fontSize: 14 }}>
                <dt style={dtStyle}>Case ID</dt>
                <dd style={ddStyle}>{selectedCase.id.slice(0, 8)}...</dd>
                <dt style={dtStyle}>User</dt>
                <dd style={ddStyle}>{selectedCase.user_id}</dd>
                <dt style={dtStyle}>Thread</dt>
                <dd style={ddStyle}>{selectedCase.thread_id}</dd>
                <dt style={dtStyle}>Detection ID</dt>
                <dd style={ddStyle}>{selectedCase.detection_id.slice(0, 8)}...</dd>
                <dt style={dtStyle}>Status</dt>
                <dd style={ddStyle}>{selectedCase.status}</dd>
                <dt style={dtStyle}>Resolution</dt>
                <dd style={ddStyle}>{selectedCase.resolution || "Pending"}</dd>
              </dl>

              {selectedCase.status === "in_review" && (
                <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                  <h4 style={{ margin: 0 }}>Decision</h4>
                  <button
                    onClick={() => handleResolve(selectedCase.id, "confirmed")}
                    style={{ ...btnStyle, background: "#e74c3c", color: "#fff" }}
                  >
                    Confirm Violation
                  </button>
                  <button
                    onClick={() => handleResolve(selectedCase.id, "false_positive")}
                    style={{ ...btnStyle, background: "#27ae60", color: "#fff" }}
                  >
                    False Positive
                  </button>
                  <button
                    onClick={() => handleResolve(selectedCase.id, "escalated")}
                    style={{ ...btnStyle, background: "#8e44ad", color: "#fff" }}
                  >
                    Escalate
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = { padding: "12px 8px", fontSize: 13, color: "#666" };
const tdStyle: React.CSSProperties = { padding: "10px 8px", fontSize: 14 };
const btnStyle: React.CSSProperties = {
  padding: "6px 12px",
  border: "1px solid #ddd",
  borderRadius: 4,
  background: "#fff",
  cursor: "pointer",
  fontSize: 13,
};
const dtStyle: React.CSSProperties = { fontWeight: 600, color: "#666", marginTop: 8 };
const ddStyle: React.CSSProperties = { margin: "2px 0 0", color: "#333" };
