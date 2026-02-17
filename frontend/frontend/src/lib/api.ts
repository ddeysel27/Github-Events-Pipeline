const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

function authHeader(): HeadersInit {
  const token = localStorage.getItem("admin_basic");
  return token ? { Authorization: `Basic ${token}` } : {};
}

async function getJSON<T>(path: string, useAuth = false): Promise<T> {
  const headers: HeadersInit = useAuth ? authHeader() : {};

  const res = await fetch(`${BASE_URL}${path}`, { headers });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} ${path}: ${text}`);
  }

  return (await res.json()) as T;
}


export const api = {
  health: () => getJSON("/health"),
  eventsPerHour: () => getJSON<any[]>("/metrics/events-per-hour"),
  eventTypes: () => getJSON<any[]>("/metrics/event-types"),
  topRepos: () => getJSON<any[]>("/metrics/top-repos"),
  topActors: () => getJSON<any[]>("/metrics/top-actors"),
  pipelineRuns: () => getJSON<any[]>("/metrics/pipeline-runs"),

  adminTables: () => getJSON<string[]>("/admin/tables", true),
  adminTable: (name: string, limit = 50, offset = 0) =>
    getJSON<{ table: string; limit: number; offset: number; rows: any[] }>(
      `/admin/table/${encodeURIComponent(name)}?limit=${limit}&offset=${offset}`,
      true
    ),
};
