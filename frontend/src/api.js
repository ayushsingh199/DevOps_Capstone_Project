// Thin fetch wrapper. All calls are relative (/api/...), so the same build works behind
// the Vite dev proxy, the Nginx container and the Kubernetes Ingress without changes.

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => `${d.loc?.at(-1)}: ${d.msg}`).join(", ")
      : body.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return body;
}

function query(params) {
  const clean = Object.entries(params).filter(([, v]) => v !== "" && v != null);
  return clean.length ? `?${new URLSearchParams(clean)}` : "";
}

export const api = {
  info: () => request("/api/info"),
  stats: () => request("/api/appointments/stats"),
  listAppointments: (filters = {}) => request(`/api/appointments${query(filters)}`),
  createAppointment: (data) =>
    request("/api/appointments", { method: "POST", body: JSON.stringify(data) }),
  updateAppointment: (id, data) =>
    request(`/api/appointments/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAppointment: (id) => request(`/api/appointments/${id}`, { method: "DELETE" }),
  listDoctors: () => request("/api/doctors"),
  createDoctor: (data) => request("/api/doctors", { method: "POST", body: JSON.stringify(data) }),
  deleteDoctor: (id) => request(`/api/doctors/${id}`, { method: "DELETE" }),
};
