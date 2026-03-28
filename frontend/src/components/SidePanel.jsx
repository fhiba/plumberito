const SESSION_TOKEN = "0x" + Math.floor(Math.random() * 0xffffffffffff).toString(16).padStart(12, "0").toUpperCase();
const BOOT_TIME = new Date().toISOString().replace("T", " ").slice(0, 19);

function StatRow({ label, value, accent }) {
  return (
    <div className="flex justify-between items-baseline border-b border-[#1e1b13] border-opacity-10 py-1.5">
      <span className="font-mono text-[9px] uppercase tracking-widest opacity-50">{label}</span>
      <span className={`font-mono text-[10px] font-bold ${accent ? "text-primary-container" : "text-[#1e1b13]"}`}>
        {value}
      </span>
    </div>
  );
}

function MiniBar({ label, pct, color = "bg-primary-container" }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between">
        <span className="font-mono text-[9px] uppercase tracking-widest opacity-50">{label}</span>
        <span className="font-mono text-[9px] text-[#1e1b13] opacity-70">{pct}%</span>
      </div>
      <div className="w-full h-1.5 bg-[#1e1b13] bg-opacity-10">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function LeftPanel() {
  return (
    <aside className="w-52 border-r-4 border-[#1e1b13] bg-surface-container flex flex-col overflow-y-auto shrink-0">
      <div className="border-b-2 border-[#1e1b13] border-opacity-30 px-4 py-3">
        <div className="font-label font-black text-[9px] uppercase tracking-[0.25em] text-primary-container">
          SESSION_DATA
        </div>
      </div>

      <div className="px-4 py-3 flex flex-col gap-0.5 border-b-2 border-[#1e1b13] border-opacity-10">
        <StatRow label="TOKEN" value={SESSION_TOKEN.slice(0, 14)} />
        <StatRow label="BOOT" value={BOOT_TIME.slice(11)} />
        <StatRow label="REGION" value="US-EAST-1" />
        <StatRow label="RUNTIME" value="PY / FASTAPI" />
        <StatRow label="PROTO" value="WS v13" />
        <StatRow label="USER" value="COMMANDER" accent />
      </div>

      <div className="px-4 py-3 border-b-2 border-[#1e1b13] border-opacity-10">
        <div className="font-label font-black text-[9px] uppercase tracking-[0.25em] opacity-40 mb-3">
          SYS_LOAD
        </div>
        <div className="flex flex-col gap-2.5">
          <MiniBar label="CPU" pct={14} />
          <MiniBar label="MEM" pct={38} />
          <MiniBar label="NET_IO" pct={7} color="bg-[#1e1b13]" />
        </div>
      </div>

      <div className="px-4 py-3 border-b-2 border-[#1e1b13] border-opacity-10">
        <div className="font-label font-black text-[9px] uppercase tracking-[0.25em] opacity-40 mb-3">
          INTEGRATIONS
        </div>
        <div className="flex flex-col gap-1.5">
          {[
            { name: "GITHUB_API", ok: true },
            { name: "OPENROUTER", ok: true },
            { name: "AWS_LAMBDA", ok: true },
            { name: "PULUMI_SDK", ok: false },
          ].map(({ name, ok }) => (
            <div key={name} className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 shrink-0 ${ok ? "bg-[#1bff00]" : "bg-outline"}`} />
              <span className="font-mono text-[9px] uppercase tracking-wider opacity-60">{name}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="px-4 py-3 mt-auto">
        <div className="font-mono text-[8px] uppercase tracking-widest opacity-20 leading-relaxed">
          PLUMBERITO v0.1.0<br />
          HACKITBA · 2025<br />
          BUILD: MVP_DEMO
        </div>
      </div>
    </aside>
  );
}

export function RightPanel() {
  return (
    <aside className="w-52 border-l-4 border-[#1e1b13] bg-surface-container flex flex-col overflow-y-auto shrink-0">
      <div className="border-b-2 border-[#1e1b13] border-opacity-30 px-4 py-3">
        <div className="font-label font-black text-[9px] uppercase tracking-[0.25em] text-primary-container">
          PIPELINE_LOG
        </div>
      </div>

      <div className="px-4 py-3 border-b-2 border-[#1e1b13] border-opacity-10">
        <div className="font-label font-black text-[9px] uppercase tracking-[0.25em] opacity-40 mb-3">
          LAST_OPS
        </div>
        <div className="flex flex-col gap-2">
          {[
            { op: "REPO_CREATE", status: "OK", ts: "—" },
            { op: "CODE_PUSH", status: "OK", ts: "—" },
            { op: "INFRA_PROV", status: "IDLE", ts: "—" },
            { op: "DEPLOY", status: "IDLE", ts: "—" },
          ].map(({ op, status }) => (
            <div key={op} className="flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase tracking-wider opacity-60">{op}</span>
              <span className={`font-mono text-[9px] font-bold ${status === "OK" ? "text-[#1bff00]" : status === "ERR" ? "text-primary-container" : "opacity-30 text-[#1e1b13]"}`}>
                {status}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="px-4 py-3 border-b-2 border-[#1e1b13] border-opacity-10">
        <div className="font-label font-black text-[9px] uppercase tracking-[0.25em] opacity-40 mb-3">
          STACK
        </div>
        <div className="flex flex-col gap-1.5">
          {["NEXT.JS", "PYTHON", "FASTAPI", "AWS EC2", "LAMBDA", "PULUMI", "OPENROUTER"].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <span className="w-1 h-1 bg-[#1e1b13] opacity-30 shrink-0" />
              <span className="font-mono text-[9px] uppercase tracking-wider opacity-50">{s}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="px-4 py-3 border-b-2 border-[#1e1b13] border-opacity-10">
        <div className="font-label font-black text-[9px] uppercase tracking-[0.25em] opacity-40 mb-3">
          NET_METRICS
        </div>
        <div className="flex flex-col gap-2.5">
          <MiniBar label="LATENCY" pct={22} color="bg-[#1e1b13]" />
          <MiniBar label="THROUGHPUT" pct={61} />
          <MiniBar label="ERR_RATE" pct={0} color="bg-[#1bff00]" />
        </div>
      </div>

      <div className="px-4 py-3 mt-auto">
        <div className="font-mono text-[8px] uppercase tracking-widest opacity-20 leading-relaxed">
          INFRA: AWS<br />
          IaC: PULUMI SDK<br />
          REPO: GITHUB REST v3
        </div>
      </div>
    </aside>
  );
}
