import { AlertTriangle, CircleCheck, Clock3, FlaskConical } from "lucide-react";

export type DataState = "live" | "demo" | "pending" | "error";

const icons = {
  live: CircleCheck,
  demo: FlaskConical,
  pending: Clock3,
  error: AlertTriangle,
};

export function StatusPill({
  state,
  label,
  compact = false,
}: {
  state: DataState;
  label: string;
  compact?: boolean;
}) {
  const Icon = icons[state];

  return (
    <span className={`status-pill status-pill--${state}${compact ? " status-pill--compact" : ""}`}>
      <Icon aria-hidden="true" size={compact ? 11 : 13} strokeWidth={2.4} />
      {label}
    </span>
  );
}
