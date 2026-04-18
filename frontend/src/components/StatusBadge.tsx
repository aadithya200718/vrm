type StatusBadgeProps = {
  children: string;
  tone?: "danger" | "warning" | "info" | "muted";
};

export function StatusBadge({
  children,
  tone = "muted",
}: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${tone}`}>{children}</span>
  );
}
