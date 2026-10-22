import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export const buttonClass = (variant: "primary" | "secondary" | "quiet" = "primary") => `ui-button ui-button-${variant}`;

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" }) {
  return <button {...props} className={`${buttonClass(variant)} ${className}`} />;
}
export function Surface({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`surface ${className}`} />;
}
export function PageHeader({ title, eyebrow, description, action }: { title: string; eyebrow?: string; description?: ReactNode; action?: ReactNode }) {
  return <header className="page-header"><div className="min-w-0">{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description && <div className="page-description">{description}</div>}</div>{action && <div className="page-action">{action}</div>}</header>;
}
export function SectionHeader({ children, description }: { children: ReactNode; description?: ReactNode }) {
  return <div className="section-header"><h2>{children}</h2>{description && <p>{description}</p>}</div>;
}
export function StatusBadge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "info" | "success" | "warning" }) {
  return <span className={`status-badge badge-${tone}`}>{children}</span>;
}
export function DataQualityNotice({ title, children, severity = "info", className = "" }: { title: string; children: ReactNode; severity?: "info" | "warning"; className?: string }) {
  return <aside aria-label={title} className={`quality-notice notice-${severity} ${className}`}><h2>{title}</h2><div>{children}</div></aside>;
}
export function KpiCard({ label, value, estimated, primary, comparison, yearComparison }: { label: string; value: string; estimated?: boolean; primary?: boolean; comparison: ReactNode; yearComparison: ReactNode }) {
  return <article className={`kpi-card ${primary ? "kpi-primary" : ""}`}><h2>{label}{estimated && <StatusBadge tone="info">추정</StatusBadge>}</h2><p className="kpi-value">{value}</p><div className="comparison-indicator">{comparison}</div><div className="comparison-indicator">{yearComparison}</div></article>;
}
export function FormField({ label, children, help }: { label: ReactNode; children: ReactNode; help?: string }) {
  return <label className="form-field"><span className="field-label">{label}</span>{children}{help && <span className="help-text">{help}</span>}</label>;
}
export function FieldGroup({ title, children }: { title: string; children: ReactNode }) {
  return <section className="field-group"><h2>{title}</h2><div className="field-grid">{children}</div></section>;
}
export function ChartContainer({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return <section aria-label={title} className="surface chart-container"><h2>{title}</h2><p>{subtitle}</p>{children}</section>;
}
