import { useEffect, useMemo, useState } from "react";
import Admin from "./Admin";
import { api } from "./lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
} from "recharts";

/**
 * Simple data loader state for each API call
 */
type LoadState<T> = { loading: boolean; error?: string; data?: T };

/**
 * App: two tabs
 * - Dashboard: charts from /metrics/*
 * - Admin: protected table viewer from /admin/*
 */
export default function App() {
  // -----------------------------
  // TAB STATE
  // -----------------------------
  const [tab, setTab] = useState<"dashboard" | "admin">("dashboard");

  // -----------------------------
  // DASHBOARD DATA STATE
  // -----------------------------
  const [topRepos, setTopRepos] = useState<LoadState<any[]>>({ loading: true });
  const [eventTypes, setEventTypes] = useState<LoadState<any[]>>({ loading: true });
  const [topActors, setTopActors] = useState<LoadState<any[]>>({ loading: true });
  const [hourly, setHourly] = useState<LoadState<any[]>>({ loading: true });
  const [runs, setRuns] = useState<LoadState<any[]>>({ loading: true });

  // -----------------------------
  // LOAD DASHBOARD DATA ONCE
  // (only when on dashboard tab)
  // -----------------------------
  useEffect(() => {
    if (tab !== "dashboard") return;

    (async () => {
      try {
        const [r, e, a, h, pr] = await Promise.all([
          api.topRepos(),
          api.eventTypes(),
          api.topActors(),
          api.eventsPerHour(),
          api.pipelineRuns(),
        ]);

        setTopRepos({ loading: false, data: r });
        setEventTypes({ loading: false, data: e });
        setTopActors({ loading: false, data: a });
        setHourly({ loading: false, data: h });
        setRuns({ loading: false, data: pr });
      } catch (err: any) {
        const msg = err?.message ?? "Unknown error";
        setTopRepos({ loading: false, error: msg });
        setEventTypes({ loading: false, error: msg });
        setTopActors({ loading: false, error: msg });
        setHourly({ loading: false, error: msg });
        setRuns({ loading: false, error: msg });
      }
    })();
  }, [tab]);

  // -----------------------------
  // DERIVED: last pipeline run
  // -----------------------------
  const lastRun = useMemo(() => {
    const arr = runs.data ?? [];
    return arr.length ? arr[0] : null;
  }, [runs.data]);

  // -----------------------------
  // RENDER: TAB BAR + CONTENT
  // -----------------------------
  return (
    <div style={{ fontFamily: "system-ui, sans-serif" }}>
      {/* Tab bar */}
      <div style={{ display: "flex", gap: 8, padding: 12 }}>
        <button onClick={() => setTab("dashboard")}>Dashboard</button>
        <button onClick={() => setTab("admin")}>Admin</button>
        <div style={{ marginLeft: "auto", opacity: 0.8 }}>
          API: <code>{import.meta.env.VITE_API_BASE_URL}</code>
        </div>
      </div>

      {/* Admin tab */}
      {tab === "admin" ? (
        <Admin />
      ) : (
        // Dashboard tab
        <div style={{ padding: 20, maxWidth: 1200, margin: "0 auto" }}>
          <header style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <h1 style={{ margin: 0 }}>GitHub Events Dashboard</h1>
          </header>

          {/* Top metrics */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 16 }}>
            <MetricCard title="Top Repos" value={topRepos.data?.length ?? "—"} />
            <MetricCard title="Event Types" value={eventTypes.data?.length ?? "—"} />
            <MetricCard title="Top Actors" value={topActors.data?.length ?? "—"} />
            <MetricCard title="Last Pipeline Run" value={lastRun ? "OK" : "—"} />
          </div>

          {/* Charts grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
            <Panel title="Top Repos" state={topRepos}>
              {/* your confirmed response keys */}
              <ChartBar data={topRepos.data ?? []} xKey="repo_name" yKey="total_events" />
            </Panel>

            <Panel title="Event Types" state={eventTypes}>
              {/* adjust keys if endpoint differs */}
              <ChartBar data={eventTypes.data ?? []} xKey="event_type" yKey="total_events" />
            </Panel>

            <Panel title="Top Actors" state={topActors}>
              {/* adjust keys if endpoint differs */}
              <ChartBar data={topActors.data ?? []} xKey="actor_login" yKey="total_events" />
            </Panel>

            <Panel title="Events Per Hour" state={hourly}>
              {/* adjust keys if endpoint differs */}
              <ChartLine data={hourly.data ?? []} xKey="hour_bucket" yKey="total_events" />
            </Panel>
          </div>

          {/* Runs table */}
          <div style={{ marginTop: 16 }}>
            <Panel title="Pipeline Runs" state={runs}>
              <RunsTable rows={runs.data ?? []} />
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}

/* -----------------------------
   Reusable UI Components
------------------------------ */

function MetricCard({ title, value }: { title: string; value: any }) {
  return (
    <div style={{ border: "1px solid #222", borderRadius: 12, padding: 12 }}>
      <div style={{ opacity: 0.7, fontSize: 12 }}>{title}</div>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function Panel<T>({ title, state, children }: { title: string; state: LoadState<T>; children: any }) {
  return (
    <div style={{ border: "1px solid #222", borderRadius: 12, padding: 12, minHeight: 320 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        {state.loading && <span style={{ opacity: 0.7 }}>Loading…</span>}
        {state.error && <span style={{ color: "tomato" }}>Error</span>}
      </div>

      {state.error ? (
        <pre style={{ whiteSpace: "pre-wrap", marginTop: 10, color: "tomato" }}>{state.error}</pre>
      ) : (
        <div style={{ marginTop: 10 }}>{children}</div>
      )}
    </div>
  );
}

function ChartBar({ data, xKey, yKey }: { data: any[]; xKey: string; yKey: string }) {
  return (
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} hide />
          <YAxis />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.08)" }}
            content={({ active, payload }) => {
              if (!active || !payload || payload.length === 0) return null;

              const row = payload[0].payload as any;     // full data row for that bar
              const name = row?.[xKey];
              const value = payload[0].value;

              return (
              <div
                style={{
                  background: "#fff",
                  color: "#111",          // <-- FIX
                  padding: 10,
                  border: "1px solid #ddd",
                  fontSize: 12,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 6 }}>{String(name)}</div>
                <div>{`${yKey}: ${value}`}</div>
              </div>
            );

            }}
          />

          <Bar dataKey={yKey} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ChartLine({ data, xKey, yKey }: { data: any[]; xKey: string; yKey: string }) {
  return (
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey={yKey} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function RunsTable({ rows }: { rows: any[] }) {
  if (!rows.length) return <div style={{ opacity: 0.7 }}>No runs found.</div>;

  const cols = Object.keys(rows[0]);

  return (
    <div style={{ overflow: "auto", maxHeight: 260 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {cols.map((h) => (
              <th key={h} style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #333", opacity: 0.8 }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((k) => (
                <td key={k} style={{ padding: 8, borderBottom: "1px solid #222" }}>
                  {String(r[k] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
