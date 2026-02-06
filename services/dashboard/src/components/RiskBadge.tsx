import React from "react";

interface RiskBadgeProps {
  score: number;
}

function getRiskBand(score: number): { label: string; color: string } {
  if (score >= 0.85) return { label: "Critical", color: "#e74c3c" };
  if (score >= 0.65) return { label: "High", color: "#e67e22" };
  if (score >= 0.40) return { label: "Medium", color: "#f39c12" };
  return { label: "Low", color: "#27ae60" };
}

export default function RiskBadge({ score }: RiskBadgeProps) {
  const { label, color } = getRiskBand(score);
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        background: color,
        color: "#fff",
      }}
    >
      {label} ({score.toFixed(2)})
    </span>
  );
}
