import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

describe("App", () => {
  it("renders the CIS Dashboard title", () => {
    render(<App />);
    expect(screen.getByText("CIS Dashboard")).toBeDefined();
  });

  it("renders navigation links", () => {
    render(<App />);
    expect(screen.getAllByText("Moderator Queue").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ops Analytics").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Executive View").length).toBeGreaterThan(0);
  });

  it("shows current role", () => {
    render(<App />);
    expect(screen.getByText("Role: admin")).toBeDefined();
  });
});
