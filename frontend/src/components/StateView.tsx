type StateViewProps = {
  title: string;
  detail: string;
  tone?: "default" | "danger";
};

export function StateView({
  title,
  detail,
  tone = "default",
}: StateViewProps) {
  return (
    <div className={`state-view ${tone === "danger" ? "state-view--danger" : ""}`}>
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}
