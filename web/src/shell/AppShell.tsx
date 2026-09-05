/** Application shell — a quiet control-plane, secondary to the system itself.
 * Semantic nav grouping (CONTROL / SYSTEM / PROOF), compact run context, hairline
 * structure. No generic "Dashboard / Analytics / Settings" template chrome. */
import { NavLink, Outlet } from "react-router-dom";
import { cn } from "@/design/ui";

const GROUPS: { heading: string; items: { to: string; label: string; end?: boolean }[] }[] = [
  { heading: "Control", items: [{ to: "/", label: "Command", end: true }] },
  {
    heading: "System",
    items: [
      { to: "/topology", label: "Topology" },
      { to: "/incidents", label: "Incidents" },
    ],
  },
  {
    heading: "Proof",
    items: [
      { to: "/evaluation", label: "Evaluation" },
      { to: "/audit", label: "Audit" },
    ],
  },
];

export function AppShell() {
  return (
    <div className="flex h-full bg-bg-base">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border-subtle bg-bg-inset">
        {/* wordmark */}
        <div className="flex items-center gap-2.5 px-4 py-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-sm border border-accent/40 bg-accent/10">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          </div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold tracking-tight text-text-primary">ARIADNE</div>
            <div className="text-[10px] tracking-wide text-text-muted">revenue recovery intelligence</div>
          </div>
        </div>

        {/* semantic nav groups */}
        <nav className="flex flex-1 flex-col gap-5 px-3 py-3">
          {GROUPS.map((g) => (
            <div key={g.heading}>
              <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                {g.heading}
              </div>
              <div className="flex flex-col">
                {g.items.map((n) => (
                  <NavLink
                    key={n.to}
                    to={n.to}
                    end={n.end}
                    className={({ isActive }) =>
                      cn(
                        "group relative rounded-md px-2 py-1.5 text-[13px] transition-colors",
                        isActive
                          ? "bg-bg-hover text-text-primary"
                          : "text-text-secondary hover:bg-bg-raised hover:text-text-primary"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <span className="flex items-center gap-2">
                        <span
                          className={cn(
                            "h-3.5 w-px rounded-full transition-colors",
                            isActive ? "bg-accent" : "bg-transparent group-hover:bg-border-strong"
                          )}
                        />
                        {n.label}
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* compact run context */}
        <div className="border-t border-border-subtle px-4 py-3">
          <div className="text-[10px] uppercase tracking-[0.14em] text-text-muted">active run</div>
          <div className="tabular mt-1 text-[11px] text-text-secondary">
            RUN-07 · A_shared_bank
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-healthy/60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-healthy" />
            </span>
            <span className="text-[10px] text-text-muted">simulated · deterministic</span>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col bg-bg-base">
        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
