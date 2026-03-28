const SESSION_TOKEN = "0x" + Math.floor(Math.random() * 0xffffffffffff).toString(16).padStart(12, "0").toUpperCase();
const BOOT_TIME = new Date().toISOString().replace("T", " ").slice(0, 19);

function SectionHeader({ label }) {
  return (
    <div className="font-label font-black text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-[0.25em] opacity-40 mb-2 xl:mb-3">
      {label}
    </div>
  );
}

function StatRow({ label, value, accent }) {
  return (
    <div className="flex justify-between items-baseline border-b border-[#1e1b13] border-opacity-10 py-1.5 xl:py-2">
      <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-widest opacity-50">{label}</span>
      <span className={`font-mono text-[10px] xl:text-xs 2xl:text-sm font-bold ${accent ? "text-primary-container" : "text-[#1e1b13]"}`}>
        {value}
      </span>
    </div>
  );
}

function MiniBar({ label, pct, color = "bg-primary-container" }) {
  return (
    <div className="flex flex-col gap-1 xl:gap-1.5">
      <div className="flex justify-between">
        <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-widest opacity-50">{label}</span>
        <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs text-[#1e1b13] opacity-70">{pct}%</span>
      </div>
      <div className="w-full h-1.5 xl:h-2 bg-[#1e1b13] bg-opacity-10">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const panelBase = "hidden lg:flex lg:flex-col lg:w-52 xl:w-64 2xl:w-72 3xl:w-80 overflow-y-auto shrink-0 bg-surface-container";
const sectionPad = "px-4 xl:px-5 2xl:px-6 py-3 xl:py-4 2xl:py-5";

export function LeftPanel() {
  return (
    <aside className={`${panelBase} border-r-4 border-[#1e1b13]`}>
      <div className="border-b-2 border-[#1e1b13] border-opacity-30 px-4 xl:px-5 2xl:px-6 py-3 xl:py-4">
        <div className="font-label font-black text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-[0.25em] text-primary-container">
          SESSION_DATA
        </div>
      </div>

      <div className={`${sectionPad} flex flex-col gap-0.5 border-b-2 border-[#1e1b13] border-opacity-10`}>
        <StatRow label="TOKEN" value={SESSION_TOKEN.slice(0, 14)} />
        <StatRow label="BOOT" value={BOOT_TIME.slice(11)} />
        <StatRow label="REGION" value="US-EAST-1" />
        <StatRow label="RUNTIME" value="PY / FASTAPI" />
        <StatRow label="PROTO" value="SSE" />
        <StatRow label="USER" value="COMMANDER" accent />
      </div>

      <div className={`${sectionPad} border-b-2 border-[#1e1b13] border-opacity-10`}>
        <SectionHeader label="SYS_LOAD" />
        <div className="flex flex-col gap-2.5 xl:gap-3">
          <MiniBar label="CPU" pct={14} />
          <MiniBar label="MEM" pct={38} />
          <MiniBar label="NET_IO" pct={7} color="bg-[#1e1b13]" />
        </div>
      </div>

      <div className={`${sectionPad} border-b-2 border-[#1e1b13] border-opacity-10`}>
        <SectionHeader label="INTEGRATIONS" />
        <div className="flex flex-col gap-1.5 xl:gap-2">
          {[
            { name: "GITHUB_API", ok: true },
            { name: "OPENROUTER", ok: true },
            { name: "AWS_LAMBDA", ok: true },
            { name: "PULUMI_SDK", ok: false },
          ].map(({ name, ok }) => (
            <div key={name} className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 xl:w-2 xl:h-2 shrink-0 ${ok ? "bg-[#1bff00]" : "bg-outline"}`} />
              <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-wider opacity-60">{name}</span>
            </div>
          ))}
        </div>
      </div>

      <div className={`${sectionPad} mt-auto`}>
        <div className="font-mono text-[8px] xl:text-[9px] 2xl:text-[10px] uppercase tracking-widest opacity-20 leading-relaxed">
          PLUMBERITO v0.1.0<br />
          HACKITBA · 2026<br />
          BUILD: MVP_DEMO
        </div>
      </div>
    </aside>
  );
}

export function RightPanel() {
  return (
    <aside className={`${panelBase} border-l-4 border-[#1e1b13]`}>
      <div className="border-b-2 border-[#1e1b13] border-opacity-30 px-4 xl:px-5 2xl:px-6 py-3 xl:py-4">
        <div className="font-label font-black text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-[0.25em] text-primary-container">
          PIPELINE_LOG
        </div>
      </div>

      <div className={`${sectionPad} border-b-2 border-[#1e1b13] border-opacity-10`}>
        <SectionHeader label="LAST_OPS" />
        <div className="flex flex-col gap-2 xl:gap-2.5">
          {[
            { op: "REPO_CREATE", status: "OK" },
            { op: "CODE_PUSH",   status: "OK" },
            { op: "INFRA_PROV",  status: "IDLE" },
            { op: "DEPLOY",      status: "IDLE" },
          ].map(({ op, status }) => (
            <div key={op} className="flex items-center justify-between">
              <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-wider opacity-60">{op}</span>
              <span className={`font-mono text-[9px] xl:text-[10px] 2xl:text-xs font-bold ${status === "OK" ? "text-[#1bff00]" : status === "ERR" ? "text-primary-container" : "opacity-30 text-[#1e1b13]"}`}>
                {status}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className={`${sectionPad} border-b-2 border-[#1e1b13] border-opacity-10`}>
        <SectionHeader label="STACK" />
        <div className="flex flex-col gap-1.5 xl:gap-2">
          {["REACT / VITE", "PYTHON", "FASTAPI", "GCP CLOUD RUN", "FIREBASE", "PULUMI", "OPENROUTER"].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <span className="w-1 h-1 xl:w-1.5 xl:h-1.5 bg-[#1e1b13] opacity-30 shrink-0" />
              <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-wider opacity-50">{s}</span>
            </div>
          ))}
        </div>
      </div>

      <div className={`${sectionPad} border-b-2 border-[#1e1b13] border-opacity-10`}>
        <SectionHeader label="NET_METRICS" />
        <div className="flex flex-col gap-2.5 xl:gap-3">
          <MiniBar label="LATENCY"    pct={22} color="bg-[#1e1b13]" />
          <MiniBar label="THROUGHPUT" pct={61} />
          <MiniBar label="ERR_RATE"   pct={0}  color="bg-[#1bff00]" />
        </div>
      </div>

      <div className={`${sectionPad} mt-auto`}>
        <div className="font-mono text-[8px] xl:text-[9px] 2xl:text-[10px] uppercase tracking-widest opacity-20 leading-relaxed">
          INFRA: AWS<br />
          IaC: PULUMI SDK<br />
          REPO: GITHUB REST v3
        </div>
      </div>
    </aside>
  );
}
