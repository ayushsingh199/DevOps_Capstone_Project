import { formatDateTime, initials, label } from "../format.js";

const NEXT_STEP = {
  scheduled: { status: "checked_in", text: "Check in" },
  checked_in: { status: "completed", text: "Complete" },
};

export default function AppointmentTable({ rows, compact, onStatus, onEdit, onDelete, empty }) {
  if (!rows.length) return <p className="empty">{empty}</p>;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Patient</th>
            <th>When</th>
            {!compact && <th>Doctor</th>}
            <th>Visit</th>
            <th>Status</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => {
            const next = NEXT_STEP[a.status];
            return (
              <tr key={a.id}>
                <td data-label="Patient">
                  <div className="patient">
                    <span className="avatar">{initials(a.patient_name)}</span>
                    <div>
                      <strong>{a.patient_name}</strong>
                      <small className="muted">{a.reason || a.patient_phone}</small>
                    </div>
                  </div>
                </td>
                <td data-label="When">
                  {formatDateTime(a.scheduled_at)}
                  <small className="muted"> · {a.duration_minutes}m</small>
                </td>
                {!compact && (
                  <td data-label="Doctor">
                    {a.doctor.full_name}
                    <small className="muted">{a.doctor.specialty}</small>
                  </td>
                )}
                <td data-label="Visit">
                  <span className={`tag ${a.visit_type}`}>{label(a.visit_type)}</span>
                </td>
                <td data-label="Status">
                  <span className={`badge ${a.status}`}>{label(a.status)}</span>
                </td>
                <td>
                  <div className="actions">
                    {next && (
                      <button className="btn small" onClick={() => onStatus(a, next.status)}>
                        {next.text}
                      </button>
                    )}
                    <button className="btn small ghost" onClick={() => onEdit(a)}>
                      Edit
                    </button>
                    <button className="btn small danger" onClick={() => onDelete(a)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
