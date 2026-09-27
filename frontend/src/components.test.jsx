import React from "react";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, describe, it, expect, vi } from "vitest";
import { SessionTable } from "./main";
import { money } from "./api";
afterEach(cleanup);
const session = {
  id: "sess-a",
  started_at: "2026-09-26T19:00:00-03:00",
  unit_id: null,
  energy_kwh: 12,
  duration_minutes: 650,
  status: "interrupted",
  eligibility: "pending",
  cost_center: "resident",
};
describe("revisão e demonstrativo", () => {
  it("identifica retenção e permite inspecionar sessão sem unidade", () => {
    const open = vi.fn();
    render(<SessionTable rows={[session]} onDetail={open} />);
    expect(screen.getByText("Não identificada")).toBeInTheDocument();
    expect(screen.getByText("Em revisão")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Detalhes sess-a" }));
    expect(open).toHaveBeenCalledWith(session);
  });
  it("informa resultado vazio de filtros", () => {
    render(<SessionTable rows={[]} onDetail={() => {}} />);
    expect(screen.getByText(/Nenhuma sessão encontrada/)).toBeInTheDocument();
  });
  it("apresenta crédito negativo sem ocultar o sinal", () => {
    expect(money(-250)).toContain("-");
    expect(money(1613)).toContain("16,13");
  });
});
