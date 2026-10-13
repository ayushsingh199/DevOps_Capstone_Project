import { STATUSES, label } from "../format.js";

export default function StatusFilter({ value, counts, onChange }) {
  const options = ["", ...STATUSES];
  return (
    <div className="chips" role="tablist" aria-label="Filter by status">
      {options.map((status) => (
        <button
          key={status || "all"}
          role="tab"
          aria-selected={value === status}
          className={`chip ${value === status ? "active" : ""}`}
          onClick={() => onChange(status)}
        >
          {status ? label(status) : "All"}
          {status && counts && <span className="chip-count">{counts[status]}</span>}
        </button>
      ))}
    </div>
  );
}
