import { useNavigate } from "@tanstack/react-router";
import { Command } from "cmdk";
import { useEffect, useState } from "react";
import { NAV, type NavPath } from "./app-shell";

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const navigate = useNavigate();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const go = (to: NavPath) => {
    onOpenChange(false);
    void navigate({ to });
  };

  if (!mounted || !open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[12vh]">
      <div
        className="anim-fade absolute inset-0 bg-foreground/35"
        onClick={() => onOpenChange(false)}
      />
      <Command
        loop
        className="anim-pop relative w-full max-w-lg overflow-hidden rounded-xl border border-border bg-popover shadow-[0_24px_60px_-20px_oklch(0.2_0.01_60/0.35)]"
      >
        <div className="flex items-center gap-3 border-b border-border px-4">
          <span className="numeric text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
            Go
          </span>
          <Command.Input
            autoFocus
            placeholder="Search pages and quick navigation..."
            className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/70"
          />
          <kbd className="numeric rounded-xs border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
            ESC
          </kbd>
        </div>

        <Command.List className="max-h-[52vh] overflow-y-auto p-2">
          <Command.Empty className="px-3 py-8 text-center text-sm text-muted-foreground">
            No matching command or page found.
          </Command.Empty>

          <Command.Group
            heading="System Pages"
            className="[&_[cmdk-group-heading]]:eyebrow [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-2"
          >
            {NAV.flatMap((s) => s.items).map((item) => (
              <Item
                key={item.to}
                onSelect={() => go(item.to)}
                label={item.label}
                meta="Navigation"
              />
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}

function Item({ label, meta, onSelect }: { label: string; meta: string; onSelect: () => void }) {
  return (
    <Command.Item
      value={`${label} ${meta}`}
      onSelect={onSelect}
      className="flex cursor-pointer items-center justify-between gap-3 rounded-md px-2.5 py-2 text-sm data-[selected=true]:bg-surface-2"
    >
      <span className="truncate">{label}</span>
      <span className="numeric shrink-0 text-[11px] text-muted-foreground">{meta}</span>
    </Command.Item>
  );
}
