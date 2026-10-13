import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import KpiCards from "./components/KpiCards.jsx";
import AppointmentTable from "./components/AppointmentTable.jsx";
import AppointmentModal from "./components/AppointmentModal.jsx";
import DoctorLoad from "./components/DoctorLoad.jsx";
import DoctorsView from "./components/DoctorsView.jsx";
import StatusFilter from "./components/StatusFilter.jsx";

const VIEWS = {
  dashboard: { title: "Clinic overview", subtitle: "Today's schedule, live on AWS EKS" },
  appointments: { title: "Appointments", subtitle: "Book, reschedule and track every visit" },
  doctors: { title: "Doctors", subtitle: "Clinicians and their current load" },
};

export default function App() {
  const [view, setView] = useState("dashboard");
  const [info, setInfo] = useState(null);
  const [stats, setStats] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [filters, setFilters] = useState({ status: "", doctor_id: "", q: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState("");

  const [reloadKey, setReloadKey] = useState(0);
  const refresh = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let active = true;
    Promise.all([api.stats(), api.listAppointments(filters), api.listDoctors()])
      .then(([s, a, d]) => {
        if (!active) return;
        setStats(s);
        setAppointments(a);
        setDoctors(d);
        setError("");
      })
      .catch((err) => active && setError(`Cannot reach the MediSlot API — ${err.message}`))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [filters, reloadKey]);

  useEffect(() => {
    api
      .info()
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  async function run(action, message) {
    try {
      await action();
      setToast(message);
      refresh();
      return true;
    } catch (err) {
      setToast(`⚠ ${err.message}`);
      return false;
    }
  }

  const changeStatus = (appt, status) =>
    run(
      () => api.updateAppointment(appt.id, { status }),
      `${appt.patient_name}: ${status.replace("_", " ")}`,
    );

  const remove = (appt) => {
    if (window.confirm(`Delete appointment for ${appt.patient_name}?`)) {
      run(() => api.deleteAppointment(appt.id), "Appointment deleted");
    }
  };

  async function save(form) {
    const ok = modal?.id
      ? await run(() => api.updateAppointment(modal.id, form), "Appointment updated")
      : await run(() => api.createAppointment(form), "Appointment booked");
    if (ok) setModal(null);
  }

  const todays = appointments.filter(
    (a) => new Date(a.scheduled_at).toDateString() === new Date().toDateString(),
  );

  return (
    <div className="layout">
      <Sidebar view={view} onNavigate={setView} info={info} healthy={!error} />

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{VIEWS[view].title}</h1>
            <p className="muted">{VIEWS[view].subtitle}</p>
          </div>
          <div className="topbar-actions">
            <input
              className="search"
              type="search"
              placeholder="Search patients or reasons…"
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              aria-label="Search appointments"
            />
            <button className="btn primary" onClick={() => setModal({})}>
              + New appointment
            </button>
          </div>
        </header>

        {error && <div className="banner error">{error}</div>}
        {loading && <div className="banner">Loading clinic data…</div>}

        {!loading && view === "dashboard" && stats && (
          <>
            <KpiCards stats={stats} />
            <div className="grid-2">
              <section className="card">
                <div className="card-head">
                  <h2>Today&apos;s schedule</h2>
                  <span className="pill">{todays.length} visits</span>
                </div>
                <AppointmentTable
                  rows={todays}
                  compact
                  onStatus={changeStatus}
                  onEdit={setModal}
                  onDelete={remove}
                  empty="No visits scheduled for today."
                />
              </section>
              <DoctorLoad load={stats.doctor_load} />
            </div>
          </>
        )}

        {!loading && view === "appointments" && (
          <section className="card">
            <div className="card-head wrap">
              <StatusFilter
                value={filters.status}
                counts={stats?.by_status}
                onChange={(status) => setFilters({ ...filters, status })}
              />
              <select
                value={filters.doctor_id}
                onChange={(e) => setFilters({ ...filters, doctor_id: e.target.value })}
                aria-label="Filter by doctor"
              >
                <option value="">All doctors</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.full_name}
                  </option>
                ))}
              </select>
            </div>
            <AppointmentTable
              rows={appointments}
              onStatus={changeStatus}
              onEdit={setModal}
              onDelete={remove}
              empty="No appointments match these filters."
            />
          </section>
        )}

        {!loading && view === "doctors" && (
          <DoctorsView
            doctors={doctors}
            load={stats?.doctor_load ?? []}
            onCreate={(d) => run(() => api.createDoctor(d), `${d.full_name} added`)}
            onDelete={(d) =>
              window.confirm(`Remove ${d.full_name}?`) &&
              run(() => api.deleteDoctor(d.id), `${d.full_name} removed`)
            }
          />
        )}
      </main>

      {modal && (
        <AppointmentModal
          appointment={modal}
          doctors={doctors}
          onSave={save}
          onClose={() => setModal(null)}
        />
      )}
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}
