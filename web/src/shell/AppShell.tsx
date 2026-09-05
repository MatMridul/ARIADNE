/** Application shell: sidebar + top bar + routed content. */
import { NavLink, Outlet } from "react-router-dom";
import { cn, StatusDot } from "@/design/ui";

const NAV = [
  { to: "/", label: "Command Center", end: true },
  { to: "/topology", label: "Payment Topology" },
  { to: "/incidents", label: "Incidents & RCA" },
  { to: "/evaluation", label: "Evaluation" },
  { to: "/audit", label: "Audit Log" },
];

export function AppShell() {
  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border-subtle bg-bg-surface">
        <div className="flex items-center gap-2 px-5 py-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 text-sm font-bold text-accent">
            A
          </div>
          <div>
            <div className="text-sm font-semibold text-text-primary">ARIADNE</div>
            <div className="text-2xs text-text-muted">Revenue Recovery Intelligence</div>
          </div>
        </div>
        <nav className="flex flex-col gap-0.5 px-2 py-2">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-bg-hover text-text-primary"
                    : "text-text-secondary hover:bg-bg-hover/60 hover:text-text-primary"
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto border-t border-border-subtle px-4 py-3">
          <div className="flex items-center gap-2 text-2xs text-text-muted">
            <StatusDot health="healthy" />
            Simulated environment
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-subtle bg-bg-surface px-6">
          <div className="text-sm font-medium text-text-secondary">
            Merchant · <span className="text-text-primary">Acme Commerce</span>
          </div>
          <div className="flex items-center gap-3 text-2xs text-text-muted">
            <span className="rounded-md border border-border-DEFAULT bg-bg-hover px-2 py-1">
              deterministic · seeded
            </span>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
