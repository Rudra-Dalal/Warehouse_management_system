import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Table({ children, minWidth = 820 }: { children: ReactNode; minWidth?: number }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm" style={{ minWidth }}>
        {children}
      </table>
    </div>
  );
}

export function THead({ cols }: { cols: { label: string; align?: "right"; width?: string }[] }) {
  return (
    <thead>
      <tr className="border-b border-border bg-surface-2/60">
        {cols.map((c) => (
          <th
            key={c.label}
            style={c.width ? { width: c.width } : undefined}
            className={cn(
              "px-4 py-2.5 text-left font-mono text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase",
              c.align === "right" && "text-right",
            )}
          >
            {c.label}
          </th>
        ))}
      </tr>
    </thead>
  );
}

export function Tr({ children }: { children: ReactNode }) {
  return (
    <tr className="group border-b border-border transition-colors last:border-0 hover:bg-surface-2/70">
      {children}
    </tr>
  );
}

export function Td({
  children,
  align,
  className,
}: {
  children: ReactNode;
  align?: "right";
  className?: string;
}) {
  return (
    <td className={cn("px-4 py-3.5", align === "right" && "text-right", className)}>{children}</td>
  );
}

export function TableFooter({ count, total }: { count: number; total: number }) {
  return (
    <div className="flex items-center justify-between border-t border-border px-4 py-3">
      <p className="numeric text-[11px] tracking-wider text-muted-foreground uppercase">
        {count} of {total} records
      </p>
      <p className="numeric text-[11px] text-muted-foreground">Page 1 / 1</p>
    </div>
  );
}
