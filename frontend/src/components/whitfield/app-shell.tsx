import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import {
  LayoutDashboard,
  Boxes,
  Package,
  Store,
  Truck,
  ClipboardList,
  ScanLine,
  Workflow,
  History,
  Users,
  Search,
  Menu,
  X,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CommandPalette } from "./command-palette";

export type NavPath =
  | "/"
  | "/inventory"
  | "/products"
  | "/sellers"
  | "/receiving"
  | "/orders"
  | "/fulfillment"
  | "/scanner"
  | "/audit"
  | "/users";

type NavItem = { to: NavPath; label: string; icon: LucideIcon };

export const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    group: "Catalog",
    items: [
      { to: "/inventory", label: "Inventory", icon: Boxes },
      { to: "/products", label: "Products", icon: Package },
      { to: "/sellers", label: "Sellers", icon: Store },
    ],
  },
  {
    group: "Operations",
    items: [
      { to: "/receiving", label: "Receiving", icon: Truck },
      { to: "/orders", label: "Orders", icon: ClipboardList },
      { to: "/fulfillment", label: "Fulfillment", icon: Workflow },
      { to: "/scanner", label: "Barcode Scanner", icon: ScanLine },
    ],
  },
  {
    group: "Governance",
    items: [
      { to: "/audit", label: "Audit Trail", icon: History },
      { to: "/users", label: "Users", icon: Users },
    ],
  },
];

function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5 focus-visible:outline-offset-4">
      <span className="grid size-7 place-items-center rounded-[5px] bg-signal">
        <span className="numeric text-[13px] leading-none font-bold text-signal-foreground">W</span>
      </span>
      <span className="flex flex-col leading-none">
        <span className="text-[13px] font-semibold tracking-[-0.01em] text-sidebar-foreground">
          Whitfield
        </span>
        <span className="numeric mt-1 text-[9px] tracking-[0.18em] text-sidebar-muted uppercase">
          Fulfillment
        </span>
      </span>
    </Link>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
      {NAV.map((section) => (
        <div key={section.group}>
          <p className="px-2.5 pb-2 font-mono text-[10px] tracking-[0.16em] text-sidebar-muted uppercase">
            {section.group}
          </p>
          <ul className="space-y-0.5">
            {section.items.map((item) => {
              const active = pathname === item.to;
              const Icon = item.icon;
              return (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    onClick={onNavigate}
                    className={cn(
                      "group relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors duration-150",
                      active
                        ? "bg-sidebar-accent font-medium text-sidebar-foreground"
                        : "text-sidebar-muted hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                    )}
                  >
                    <span
                      className={cn(
                        "absolute top-1/2 left-0 h-4 w-[2px] -translate-y-1/2 rounded-full transition-all duration-200",
                        active ? "bg-signal opacity-100" : "opacity-0",
                      )}
                    />
                    <Icon className="size-4 shrink-0" strokeWidth={1.75} />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function SidebarFooter() {
  return (
    <div className="border-t border-sidebar-border px-4 py-3.5">
      <div className="flex items-center gap-2.5">
        <span className="grid size-7 place-items-center rounded-full bg-sidebar-accent text-[11px] font-semibold text-sidebar-foreground">
          RD
        </span>
        <span className="min-w-0 flex-1 leading-tight">
          <span className="block truncate text-xs font-medium text-sidebar-foreground">
            Rudra Dalal
          </span>
          <span className="numeric block text-[10px] tracking-wider text-sidebar-muted uppercase">
            Admin · All warehouses
          </span>
        </span>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar — desktop */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        <div className="flex h-14 items-center border-b border-sidebar-border px-4">
          <Wordmark />
        </div>
        <NavList />
        <SidebarFooter />
      </aside>

      {/* Sidebar — mobile */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="anim-fade absolute inset-0 bg-foreground/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-64 flex-col bg-sidebar shadow-xl duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] animate-in slide-in-from-left">
            <div className="flex h-14 items-center justify-between border-b border-sidebar-border px-4">
              <Wordmark />
              <button
                onClick={() => setMobileOpen(false)}
                className="text-sidebar-muted hover:text-sidebar-foreground"
                aria-label="Close navigation"
              >
                <X className="size-4" />
              </button>
            </div>
            <NavList onNavigate={() => setMobileOpen(false)} />
            <SidebarFooter />
          </div>
        </div>
      ) : null}

      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur-md sm:px-6">
          <button
            className="text-muted-foreground hover:text-foreground lg:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="size-5" />
          </button>

          <button
            onClick={() => setPaletteOpen(true)}
            className="group flex h-9 max-w-md flex-1 items-center gap-2.5 rounded-md border border-border bg-surface px-3 text-left text-sm text-muted-foreground transition-colors hover:border-border-strong hover:bg-surface-2"
          >
            <Search className="size-4" strokeWidth={1.75} />
            <span className="flex-1 truncate">Search SKUs, orders, sellers…</span>
            <kbd className="numeric hidden rounded-xs border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground sm:block">
              ⌘K
            </kbd>
          </button>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden items-center gap-2 md:flex">
              <span className="pulse-dot size-1.5 rounded-full bg-ok" />
              <span className="numeric text-[11px] tracking-wider text-muted-foreground uppercase">
                Reno · Columbus online
              </span>
            </span>
            <span className="numeric hidden rounded-md border border-border bg-surface px-2 py-1 text-[11px] tracking-wider text-muted-foreground uppercase sm:block">
              Shift A
            </span>
          </div>
        </header>

        <main key={pathname} className="anim-fade px-4 py-7 sm:px-6 lg:px-10 lg:py-9">
          <div className="mx-auto max-w-[1400px] space-y-7">{children}</div>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
