import { useState } from "react";
import { initials } from "../format.js";

const EMPTY = { full_name: "", specialty: "", room: "" };

export default function DoctorsView({ doctors, load, onCreate, onDelete }) {
  const [form, setForm] = useState(EMPTY);
  const active = Object.fromEntries(load.map((l) => [l.doctor_id, l.active_appointments]));

  async function submit(e) {
    e.preventDefault();
    if (await onCreate(form)) setForm(EMPTY);
  }

  return (
    <>
      <form className="card inline-form" onSubmit={submit} aria-label="Add doctor">
        <input
          required
          minLength={3}
          placeholder="Dr. Full Name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
        />
        <input
          required
          minLength={2}
          placeholder="Specialty"
          value={form.specialty}
          onChange={(e) => setForm({ ...form, specialty: e.target.value })}
        />
        <input
          required
          placeholder="Room"
          value={form.room}
          onChange={(e) => setForm({ ...form, room: e.target.value })}
        />
        <button className="btn primary">Add doctor</button>
      </form>

      <section className="doctor-grid">
        {doctors.map((d) => (
          <article key={d.id} className="card doctor">
            <span className="avatar large">{initials(d.full_name)}</span>
            <strong>{d.full_name}</strong>
            <span className="muted">{d.specialty}</span>
            <div className="doctor-meta">
              <span className="pill">Room {d.room}</span>
              <span className="pill">{active[d.id] ?? 0} active</span>
            </div>
            <button className="btn small danger" onClick={() => onDelete(d)}>
              Remove
            </button>
          </article>
        ))}
      </section>
    </>
  );
}
