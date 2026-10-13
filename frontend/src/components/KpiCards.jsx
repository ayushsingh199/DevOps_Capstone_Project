export default function KpiCards({ stats }) {
  const cards = [
    { label: "Visits today", value: stats.today, hint: "Across all doctors", tone: "teal" },
    { label: "Upcoming", value: stats.upcoming, hint: "Scheduled, not yet seen", tone: "blue" },
    {
      label: "Checked in",
      value: stats.by_status.checked_in,
      hint: "Waiting room right now",
      tone: "amber",
    },
    {
      label: "Completion rate",
      value: `${stats.completion_rate}%`,
      hint: `${stats.by_status.no_show} no-shows recorded`,
      tone: "green",
    },
  ];
  return (
    <section className="kpis" aria-label="Key metrics">
      {cards.map((card) => (
        <article key={card.label} className={`kpi ${card.tone}`}>
          <span className="kpi-label">{card.label}</span>
          <strong className="kpi-value">{card.value}</strong>
          <span className="kpi-hint">{card.hint}</span>
        </article>
      ))}
    </section>
  );
}
