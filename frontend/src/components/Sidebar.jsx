const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "▦" },
  { id: "appointments", label: "Appointments", icon: "◷" },
  { id: "doctors", label: "Doctors", icon: "✚" },
];

export default function Sidebar({ view, onNavigate, info, healthy }) {
  const version = info?.version ?? "unknown";
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="logo" aria-hidden>
          ✚
        </span>
        <div>
          <strong>MediSlot</strong>
          <small>Clinic scheduling</small>
        </div>
      </div>

      <nav>
        {NAV.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${view === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
          >
            <span aria-hidden>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="build-card" title="Build metadata served by /api/info">
        <div className="build-row">
          <span className={`dot ${healthy ? "ok" : "down"}`} />
          API {healthy ? "online" : "unreachable"}
        </div>
        <div className="build-row">
          <span className="muted">Build</span>
          <code>{version.slice(0, 7)}</code>
        </div>
        <div className="build-row">
          <span className="muted">Env</span>
          <code>{info?.environment ?? "—"}</code>
        </div>
      </div>
    </aside>
  );
}
