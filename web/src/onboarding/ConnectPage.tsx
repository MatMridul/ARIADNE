/** Connect payment infrastructure — the topology-ingestion front door.
 * A thin, honest infrastructure-mapping workflow: paste a topology manifest,
 * validate it against the real /api/topology/import boundary, and on success see
 * the normalized topology + shared dependencies, then open the Command Center.
 * Uses the ARIA instrument visual language — no SaaS onboarding cards, no fake
 * connection statuses, no illustrations. In-memory only (no persistence claimed). */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { cn } from "@/design/ui";
import { importTopology, type ImportResult } from "@/lib";

const EXAMPLE_MANIFEST = {
  merchant: { id: "mx_1", name: "Acme Commerce" },
  methods: [
    { id: "upi", name: "UPI" },
    { id: "card", name: "Card" },
    { id: "netbanking", name: "Netbanking" },
  ],
  psps: [
    { id: "psp_1", name: "PSP-1" },
    { id: "psp_2", name: "PSP-2" },
    { id: "psp_3", name: "PSP-3" },
  ],
  banks: [
    { id: "bank_A", name: "Bank-A", role: "acquirer" },
    { id: "bank_B", name: "Bank-B", role: "acquirer" },
  ],
  routes: [
    { method: "upi", psp: "psp_1", bank: "bank_A" },
    { method: "upi", psp: "psp_2", bank: "bank_A" },
    { method: "upi", psp: "psp_3", bank: "bank_B" },
    { method: "card", psp: "psp_1", bank: "bank_A" },
    { method: "card", psp: "psp_2", bank: "bank_A" },
    { method: "card", psp: "psp_3", bank: "bank_B" },
    { method: "netbanking", psp: "psp_1", bank: "bank_A" },
    { method: "netbanking", psp: "psp_2", bank: "bank_A" },
    { method: "netbanking", psp: "psp_3", bank: "bank_B" },
  ],
};

type State =
  | { phase: "edit" }
  | { phase: "validating" }
  | { phase: "valid"; result: ImportResult }
  | { phase: "invalid"; errors: string[] };

export function ConnectPage() {
  const navigate = useNavigate();
  const [text, setText] = useState(() => JSON.stringify(EXAMPLE_MANIFEST, null, 2));
  const [state, setState] = useState<State>({ phase: "edit" });

  async function validate() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      setState({ phase: "invalid", errors: [`manifest is not valid JSON: ${(e as Error).message}`] });
      return;
    }
    setState({ phase: "validating" });
    try {
      const result = await importTopology(parsed);
      setState({ phase: "valid", result });
    } catch (e) {
      setState({ phase: "invalid", errors: (e as Error).message.split("\n") });
    }
  }

  return (
    <div className="flex h-full flex-col bg-bg-base">
      {/* quiet header */}
      <div className="border-b border-border-subtle px-6 py-4">
        <h1 className="text-[13px] font-semibold uppercase tracking-[0.14em] text-text-secondary">
          Connect payment infrastructure
        </h1>
        <p className="mt-1 text-[12px] text-text-muted">
          Define the dependencies ARIA will reason over. Provide a topology manifest
          — methods, PSPs, banks, and the method → PSP → bank routes between them.
        </p>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* manifest editor */}
        <section className="flex min-w-0 flex-1 flex-col border-r border-border-subtle">
          <div className="flex items-center justify-between border-b border-border-subtle px-5 py-2.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
              Topology manifest · JSON
            </span>
            <button
              onClick={() => { setText(JSON.stringify(EXAMPLE_MANIFEST, null, 2)); setState({ phase: "edit" }); }}
              className="text-[10px] uppercase tracking-wide text-text-muted hover:text-text-secondary"
            >
              reset to example
            </button>
          </div>
          <textarea
            value={text}
            onChange={(e) => { setText(e.target.value); if (state.phase !== "edit") setState({ phase: "edit" }); }}
            spellCheck={false}
            aria-label="Topology manifest JSON"
            className="tabular min-h-0 flex-1 resize-none bg-bg-inset px-5 py-4 text-[12px] leading-relaxed text-text-secondary outline-none focus:text-text-primary"
          />
          <div className="flex items-center gap-3 border-t border-border-subtle px-5 py-3">
            <button
              onClick={validate}
              disabled={state.phase === "validating"}
              className="rounded-[3px] border border-accent/50 bg-accent/15 px-4 py-1.5 text-[12px] font-medium text-accent transition-colors hover:bg-accent/25 disabled:opacity-50"
            >
              {state.phase === "validating" ? "Validating…" : "Validate topology"}
            </button>
            <span className="text-[10px] text-text-muted">
              validated against the live ingestion boundary · held in memory, not persisted
            </span>
          </div>
        </section>

        {/* result rail */}
        <aside className="flex w-[380px] shrink-0 flex-col overflow-y-auto bg-bg-inset px-5 py-4">
          {state.phase === "edit" && (
            <p className="text-[12px] text-text-muted">
              Validate the manifest to map it into ARIA's dependency graph.
            </p>
          )}

          {state.phase === "validating" && (
            <p className="text-[12px] text-text-secondary">Validating topology…</p>
          )}

          {state.phase === "invalid" && (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-down" />
                <span className="text-[11px] font-semibold uppercase tracking-wide text-down">
                  Topology invalid · {state.errors.length} issue{state.errors.length === 1 ? "" : "s"}
                </span>
              </div>
              <ul className="space-y-1.5">
                {state.errors.map((e, i) => (
                  <li key={i} className="tabular text-[11px] leading-snug text-text-secondary">
                    <span className="text-down">•</span> {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {state.phase === "valid" && (
            <ValidResult result={state.result} onOpen={() => navigate("/")} />
          )}
        </aside>
      </div>
    </div>
  );
}

function ValidResult({ result, onOpen }: { result: ImportResult; onOpen: () => void }) {
  const c = result.counts;
  const sharedIds = Object.keys(result.shared_dependencies);
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
      <div className="mb-3 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-healthy" />
        <span className="text-[11px] font-semibold uppercase tracking-wide text-healthy">
          Topology validated
        </span>
      </div>

      <div className="text-[15px] font-semibold tracking-tight text-text-primary">
        {c.methods} payment methods · {c.psps} PSPs · {c.banks} banking dependencies
      </div>
      <div className="tabular mt-0.5 text-[11px] text-text-muted">{c.routes} routes mapped</div>

      {/* shared dependencies — the thing ARIA reasons over */}
      <div className="mt-4 border-t border-border-subtle pt-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
          Shared dependencies detected
        </div>
        {sharedIds.length === 0 ? (
          <p className="mt-1.5 text-[11px] text-text-muted">
            None — no bank is shared by more than one PSP. ARIA's relational edge is
            strongest when a bank is shared.
          </p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {sharedIds.map((bid) => (
              <li key={bid} className="flex items-center gap-2 text-[11px]">
                <span className="tabular font-medium text-info">{bid}</span>
                <span className="text-text-muted">shared by</span>
                <span className="tabular text-text-secondary">
                  {result.shared_dependencies[bid].join(", ")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <button
        onClick={onOpen}
        className="mt-5 w-full rounded-[3px] border border-accent/50 bg-accent/15 px-4 py-2 text-[12px] font-medium text-accent transition-colors hover:bg-accent/25"
      >
        Open Command Center →
      </button>
      <p className="mt-2 text-[10px] text-text-muted">
        The Command Center visualizes the same topology through ARIA's payment network.
      </p>
    </motion.div>
  );
}
