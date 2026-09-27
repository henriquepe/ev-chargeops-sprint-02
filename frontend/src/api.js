export async function request(path, token, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? body.detail.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join("; ")
      : body.detail;
    const error = new Error(detail || "Não foi possível concluir a operação.");
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}
export const money = (cents = 0) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    cents / 100,
  );
export const number = (n = 0, digits = 1) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: digits }).format(n);
export const dateTime = (value) =>
  new Date(value).toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
export const monthName = (month) =>
  new Date(`${month}-02T12:00:00`).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
