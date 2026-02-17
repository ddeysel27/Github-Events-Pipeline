import { useEffect, useState } from "react";
import { api } from "./lib/api";

export default function Admin() {
  // ---- auth state ----
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [authed, setAuthed] = useState(!!localStorage.getItem("admin_basic"));

  // ---- table state ----
  const [tables, setTables] = useState<string[]>([]);
  const [table, setTable] = useState<string>("");
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState<string>("");

  // ---- pagination ----
  const [offset, setOffset] = useState(0);
  const limit = 50;

  function login() {
    const token = btoa(`${user}:${pass}`);
    localStorage.setItem("admin_basic", token);
    setAuthed(true);
  }

  function logout() {
    localStorage.removeItem("admin_basic");
    setAuthed(false);
    setTables([]);
    setRows([]);
    setTable("");
    setOffset(0);
    setError("");
  }

  async function loadTables() {
    setError("");
    const t = await api.adminTables();
    setTables(t);
    const first = t[0] ?? "";
    setTable(first);
    setOffset(0);
  }

  async function loadTable(name: string, off: number) {
    setError("");
    const res = await api.adminTable(name, limit, off);
    setRows(res.rows);
  }

  // load tables once after auth
  useEffect(() => {
    if (!authed) return;
    loadTables().catch((e: any) => setError(e.message));
  }, [authed]);

  // load rows when table or offset changes
  useEffect(() => {
    if (!authed || !table) return;
    loadTable(table, offset).catch((e: any) => setError(e.message));
  }, [authed, table, offset]);

  if (!authed) {
    return (
      <div style={{ padding: 20 }}>
        <h2>Admin Login</h2>
        <input placeholder="username" value={user} onChange={(e) => setUser(e.target.value)} />
        <br />
        <input placeholder="password" type="password" value={pass} onChange={(e) => setPass(e.target.value)} />
        <br />
        <button onClick={login}>Login</button>
      </div>
    );
  }

  const cols = rows[0] ? Object.keys(rows[0]) : [];

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Admin: Postgres Tables</h2>
        <button onClick={logout}>Logout</button>
      </div>

      {error && <div style={{ color: "tomato", marginTop: 8 }}>{error}</div>}

      <div style={{ display: "flex", gap: 12, marginTop: 12, alignItems: "center" }}>
        <select
          value={table}
          onChange={(e) => {
            setTable(e.target.value);
            setOffset(0);
          }}
        >
          {tables.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0}>
          Prev
        </button>
        <button onClick={() => setOffset(offset + limit)} disabled={rows.length < limit}>
          Next
        </button>

        <span style={{ opacity: 0.7, fontSize: 12 }}>offset: {offset} | limit: {limit}</span>
      </div>

      {/* Table viewer */}
      <div
        style={{
          marginTop: 12,
          overflow: "auto",
          maxHeight: 520,
          border: "1px solid #222",
          borderRadius: 12,
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {cols.map((col) => (
                <th
                  key={col}
                  style={{
                    textAlign: "left",
                    padding: 10,
                    borderBottom: "1px solid #333",
                    position: "sticky",
                    top: 0,
                    background: "#111",
                    fontSize: 12,
                    opacity: 0.9,
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {cols.map((col) => (
                  <td key={col} style={{ padding: 10, borderBottom: "1px solid #222", fontSize: 12 }}>
                    {String(r[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {!rows.length && <div style={{ padding: 12, opacity: 0.7 }}>No rows returned.</div>}
      </div>
    </div>
  );
}
