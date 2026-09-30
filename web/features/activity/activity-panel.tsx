import { SectorHeader } from "@/components/system/sector-header";

export type ActivityEvent = { message: string; timestamp?: string | null };
export function ActivityPanel({ events = [], available = true }: { events?: ActivityEvent[]; available?: boolean }) {
  return <section className="atlas-card atlas-activity-card atlas-feature-3d atlas-mobile-reference-card" id="activity">
    <SectorHeader title="Recent Activity" kind="activity" />
    {!available ? <div className="atlas-empty-line atlas-mobile-reference-empty">Activity unavailable</div> : events.length === 0 ? <div className="atlas-empty-line atlas-mobile-reference-empty">No recent activity</div> :
      <ul className="atlas-activity-list">{events.map((event, i) => <li key={i}>{event.message}{event.timestamp && <time dateTime={event.timestamp}>{event.timestamp}</time>}</li>)}</ul>}
  </section>;
}
