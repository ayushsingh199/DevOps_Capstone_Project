import { useState } from "react";
import { STATUSES, VISIT_TYPES, label, toLocalInput } from "../format.js";

function defaultSlot() {
  const d = new Date();
  d.setHours(d.getHours() + 1, 0, 0, 0);
  return toLocalInput(d);
}

export default function AppointmentModal({ appointment, doctors, onSave, onClose }) {
  const editing = Boolean(appointment.id);
  const [form, setForm] = useState({
    patient_name: appointment.patient_name ?? "",
    patient_phone: appointment.patient_phone ?? "",
    doctor_id: appointment.doctor_id ?? doctors[0]?.id ?? "",
    scheduled_at: appointment.scheduled_at ? toLocalInput(appointment.scheduled_at) : defaultSlot(),
    duration_minutes: appointment.duration_minutes ?? 30,
    visit_type: appointment.visit_type ?? "consultation",
    status: appointment.status ?? "scheduled",
    reason: appointment.reason ?? "",
  });
  const [saving, setSaving] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    const payload = {
      ...form,
      doctor_id: Number(form.doctor_id),
      duration_minutes: Number(form.duration_minutes),
      scheduled_at: new Date(form.scheduled_at).toISOString(),
      reason: form.reason || null,
    };
    if (!editing) delete payload.status;
    await onSave(payload);
    setSaving(false);
  }

  return (
    <div className="overlay" onClick={onClose}>
      <form
        className="modal"
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        aria-label={editing ? "Edit appointment" : "New appointment"}
      >
        <div className="card-head">
          <h2>{editing ? `Edit appointment #${appointment.id}` : "Book an appointment"}</h2>
          <button type="button" className="btn ghost small" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="form-grid">
          <label>
            Patient name
            <input
              required
              minLength={2}
              value={form.patient_name}
              onChange={set("patient_name")}
            />
          </label>
          <label>
            Phone
            <input
              required
              pattern="^\+?[0-9 \-]{7,20}$"
              placeholder="+91 98765 43210"
              value={form.patient_phone}
              onChange={set("patient_phone")}
            />
          </label>
          <label>
            Doctor
            <select value={form.doctor_id} onChange={set("doctor_id")}>
              {doctors.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name} — {d.specialty}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date &amp; time
            <input
              type="datetime-local"
              required
              value={form.scheduled_at}
              onChange={set("scheduled_at")}
            />
          </label>
          <label>
            Duration
            <select value={form.duration_minutes} onChange={set("duration_minutes")}>
              {[15, 30, 45, 60, 90].map((m) => (
                <option key={m} value={m}>
                  {m} minutes
                </option>
              ))}
            </select>
          </label>
          <label>
            Visit type
            <select value={form.visit_type} onChange={set("visit_type")}>
              {VISIT_TYPES.map((v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          </label>
          {editing && (
            <label>
              Status
              <select value={form.status} onChange={set("status")}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {label(s)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="span-2">
            Reason for visit
            <textarea rows={2} maxLength={500} value={form.reason} onChange={set("reason")} />
          </label>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={saving}>
            {saving ? "Saving…" : editing ? "Save changes" : "Book appointment"}
          </button>
        </div>
      </form>
    </div>
  );
}
