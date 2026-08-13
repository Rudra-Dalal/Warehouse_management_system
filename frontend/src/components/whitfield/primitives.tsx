import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="anim-rise flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="title-page mt-2 text-foreground">{title}</h1>
        {description ? (
          <p className="mt-1.5 max-w-xl text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function Panel({
  title,
  meta,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  meta?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("panel overflow-hidden", className)}>
      {title ? (
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <h2 className="eyebrow">{title}</h2>
          {meta ? <div className="text-xs text-muted-foreground">{meta}</div> : null}
        </div>
      ) : null}
      <div className={cn(bodyClassName)}>{children}</div>
    </section>
  );
}

type Tone = "neutral" | "ok" | "warn" | "danger" | "info" | "signal";

const toneStyles: Record<Tone, string> = {
  neutral: "text-muted-foreground before:bg-border-strong",
  ok: "text-ok before:bg-ok",
  warn: "text-warn before:bg-warn",
  danger: "text-danger before:bg-danger",
  info: "text-info before:bg-info",
  signal: "text-signal before:bg-signal",
};

export function StatusPill({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm bg-surface-2 px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase",
        "before:size-1.5 before:rounded-full before:content-['']",
        toneStyles[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "signal";
  size?: "sm" | "md";
}) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md border font-medium whitespace-nowrap transition-[background-color,color,border-color,transform] duration-150 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.985] disabled:pointer-events-none disabled:opacity-50",
        size === "sm" ? "h-8 px-2.5 text-xs" : "h-9 px-3.5 text-sm",
        variant === "primary" &&
          "border-primary bg-primary text-primary-foreground hover:bg-primary/90",
        variant === "signal" &&
          "border-signal bg-signal text-signal-foreground hover:bg-signal/90",
        variant === "secondary" &&
          "border-border bg-surface text-foreground hover:border-border-strong hover:bg-surface-2",
        variant === "ghost" &&
          "border-transparent bg-transparent text-muted-foreground hover:bg-surface-2 hover:text-foreground",
        className,
      )}
    />
  );
}

export function Metric({
  value,
  label,
  tone,
  size = "lg",
}: {
  value: ReactNode;
  label: string;
  tone?: "signal" | "danger";
  size?: "lg" | "sm";
}) {
  return (
    <div>
      <div
        className={cn(
          "numeric font-semibold",
          size === "lg" ? "display-lg" : "text-2xl leading-none tracking-tight",
          tone === "signal" && "text-signal",
          tone === "danger" && "text-danger",
        )}
      >
        {value}
      </div>
      <div className="mt-2 text-xs tracking-wide text-muted-foreground uppercase">{label}</div>
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="eyebrow">{label}</span>
      <div className="mt-2">{children}</div>
      {hint ? <span className="mt-1.5 block text-xs text-muted-foreground">{hint}</span> : null}
    </label>
  );
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "h-9 w-full rounded-md border border-border bg-surface px-3 text-sm text-foreground transition-colors placeholder:text-muted-foreground/70 hover:border-border-strong focus:border-signal focus:outline-none",
        className,
      )}
    />
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="anim-fade flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="numeric text-xs tracking-[0.3em] text-muted-foreground uppercase">
        — no records —
      </div>
      <h3 className="mt-4 text-base font-semibold">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3.5">
          <div className="h-3 w-24 animate-pulse rounded-xs bg-surface-2" />
          <div className="h-3 flex-1 animate-pulse rounded-xs bg-surface-2" />
          <div className="h-3 w-16 animate-pulse rounded-xs bg-surface-2" />
        </div>
      ))}
    </div>
  );
}

export function Delta({ value }: { value: number }) {
  const positive = value >= 0;
  return (
    <span className={cn("numeric text-xs", positive ? "text-ok" : "text-danger")}>
      {positive ? "▲" : "▼"} {Math.abs(value)}%
    </span>
  );
}
