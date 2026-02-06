import React from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import ModeratorQueue from "./pages/ModeratorQueue";
import OpsAnalytics from "./pages/OpsAnalytics";
import ExecutiveDashboard from "./pages/ExecutiveDashboard";

type UserRole = "moderator" | "ops" | "admin" | "executive";

const ROLE_ACCESS: Record<string, UserRole[]> = {
  "/moderator": ["moderator", "ops", "admin"],
  "/ops": ["ops", "admin"],
  "/executive": ["executive", "admin"],
};

function App() {
  // In production, role comes from auth context
  const [currentRole] = React.useState<UserRole>("admin");

  const canAccess = (path: string) => {
    const allowed = ROLE_ACCESS[path];
    return !allowed || allowed.includes(currentRole);
  };

  return (
    <BrowserRouter>
      <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
        {/* Sidebar Navigation */}
        <nav style={{
          width: 220,
          background: "#1a1a2e",
          color: "#eee",
          padding: "20px 0",
          display: "flex",
          flexDirection: "column",
        }}>
          <div style={{ padding: "0 20px 20px", borderBottom: "1px solid #333" }}>
            <h2 style={{ margin: 0, fontSize: 16 }}>CIS Dashboard</h2>
            <span style={{ fontSize: 12, color: "#888" }}>Role: {currentRole}</span>
          </div>
          <div style={{ padding: "10px 0" }}>
            {canAccess("/moderator") && (
              <NavLink to="/moderator" style={navStyle}>
                Moderator Queue
              </NavLink>
            )}
            {canAccess("/ops") && (
              <NavLink to="/ops" style={navStyle}>
                Ops Analytics
              </NavLink>
            )}
            {canAccess("/executive") && (
              <NavLink to="/executive" style={navStyle}>
                Executive View
              </NavLink>
            )}
          </div>
        </nav>

        {/* Main Content */}
        <main style={{ flex: 1, padding: 24, background: "#f5f5f5" }}>
          <Routes>
            <Route path="/" element={<ModeratorQueue />} />
            <Route path="/moderator" element={<ModeratorQueue />} />
            <Route path="/ops" element={<OpsAnalytics />} />
            <Route path="/executive" element={<ExecutiveDashboard />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

const navStyle: React.CSSProperties = {
  display: "block",
  padding: "10px 20px",
  color: "#ccc",
  textDecoration: "none",
  fontSize: 14,
};

export default App;
