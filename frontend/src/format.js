export const STATUSES = ["scheduled", "checked_in", "completed", "cancelled", "no_show"];
export const VISIT_TYPES = ["consultation", "follow_up", "emergency", "lab_review", "vaccination"];

export const label = (value) => value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// <input type="datetime-local"> works in local time without a zone suffix.
export function toLocalInput(date) {
  const d = new Date(date);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export const initials = (name) =>
  name
    .replace(/^Dr\.\s*/, "")
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
