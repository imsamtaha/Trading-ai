export type ActivityEvent = { message: string; timestamp?: string | null };
export function ActivityPanel({ events = [], available = true }: { events?: ActivityEvent[]; available?: boolean }) {
  return <section className="atlas-card atlas-activity-card" id="activity">
    <div className="atlas-section-heading"><div><span className="atlas-card-label">System feed</span><h2>Recent Activity</h2></div></div>
    {!available ? <div className="atlas-empty-line">Activity unavailable</div> : events.length === 0 ? <div className="atlas-empty-line">No recent activity</div> :
      <ul className="atlas-activity-list">{events.map((event, i) => <li key={i}>{event.message}{event.timestamp && <time dateTime={event.timestamp}>{event.timestamp}</time>}</li>)}</ul>}
  </section>;
}
