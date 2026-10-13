import { initials } from "../format.js";

export default function DoctorLoad({ load }) {
  const max = Math.max(1, ...load.map((d) => d.active_appointments));
  return (
    <section className="card">
      <div className="card-head">
        <h2>Doctor load</h2>
        <span className="pill">active bookings</span>
      </div>
      <ul className="load-list">
        {load.map((d) => (
          <li key={d.doctor_id}>
            <span className="avatar soft">{initials(d.full_name)}</span>
            <div className="load-body">
              <div className="load-head">
                <strong>{d.full_name}</strong>
                <span>{d.active_appointments}</span>
              </div>
              <small className="muted">{d.specialty}</small>
              <div className="bar">
                <span style={{ width: `${(d.active_appointments / max) * 100}%` }} />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
