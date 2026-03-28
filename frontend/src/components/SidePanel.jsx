const panelBase = "hidden lg:flex lg:flex-col lg:w-52 xl:w-64 2xl:w-72 3xl:w-80 overflow-y-auto shrink-0 bg-surface-container";
const sectionPad = "px-4 xl:px-5 2xl:px-6 py-3 xl:py-4 2xl:py-5";

const CHAT_HISTORY = [
  { id: 1, label: "Generación SPA Marketplace",   time: "HOY 09:14" },
  { id: 2, label: "Deploy API REST + Firebase",    time: "HOY 08:31" },
  { id: 3, label: "Infra AWS Lambda + API GW",     time: "AYER 17:52" },
  { id: 4, label: "Landing page SaaS startup",     time: "AYER 11:20" },
  { id: 5, label: "Repo monorepo + CI/CD actions", time: "MAR 14:05" },
];

export function LeftPanel() {
  return (
    <aside className={`${panelBase} border-r-4 border-[#1e1b13]`}>
      <div className="border-b-2 border-[#1e1b13] border-opacity-30 px-4 xl:px-5 2xl:px-6 py-3 xl:py-4">
        <div className="font-label font-black text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-[0.25em] text-primary-container">
          CHAT_HISTORY
        </div>
      </div>

      <div className={`${sectionPad}`}>
        <div className="flex flex-col gap-0.5">
          {CHAT_HISTORY.map(({ id, label, time }) => (
            <div
              key={id}
              className="flex flex-col gap-0.5 px-2 py-1.5 xl:py-2 border border-transparent hover:border-[#1e1b13] hover:border-opacity-20 hover:bg-[#1e1b13] hover:bg-opacity-5 cursor-pointer"
            >
              <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs leading-snug opacity-70 truncate">{label}</span>
              <span className="font-mono text-[8px] xl:text-[9px] 2xl:text-[10px] opacity-30 uppercase tracking-widest">{time}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

export function RightPanel({ steps = [], streaming = false }) {
  return (
    <aside className={`${panelBase} border-l-4 border-[#1e1b13]`}>
      <div className="border-b-2 border-[#1e1b13] border-opacity-30 px-4 xl:px-5 2xl:px-6 py-3 xl:py-4 flex items-center justify-between">
        <div className="font-label font-black text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-[0.25em] text-primary-container">
          PIPELINE
        </div>
        {streaming && (
          <span className="font-mono text-[8px] xl:text-[9px] text-[#7a5230] animate-pulse">● LIVE</span>
        )}
      </div>

      <div className={`${sectionPad} flex flex-col gap-0`}>
        {steps.length === 0 ? (
          <div className="font-mono text-[9px] xl:text-[10px] opacity-20 uppercase tracking-widest">
            IDLE
          </div>
        ) : (
          steps.map((s, i) => {
            const isLast = i === steps.length - 1;
            const isActive = isLast && !s.done && streaming;
            const isDone = s.done;

            return (
              <div key={s.step} className="flex gap-3 relative">
                {i < steps.length - 1 && (
                  <div className="absolute left-[7px] top-5 bottom-0 w-px bg-[#1e1b13] opacity-10" />
                )}

                <div className="mt-1 shrink-0">
                  <div className={`w-3.5 h-3.5 border-2 flex items-center justify-center
                    ${isDone
                      ? "border-[#7a5230] bg-[#7a5230]"
                      : isActive
                      ? "border-primary-container animate-pulse"
                      : "border-[#1e1b13] opacity-20"}`}
                  >
                    {isDone && (
                      <span className="text-[#1e1b13] font-black" style={{ fontSize: "7px", lineHeight: 1 }}>✓</span>
                    )}
                  </div>
                </div>

                <div className={`pb-4 flex flex-col gap-1 ${!isDone && !isActive ? "opacity-25" : ""}`}>
                  <span className={`font-mono text-[8px] xl:text-[9px] font-bold uppercase tracking-widest
                    ${isDone ? "text-[#7a5230]" : isActive ? "text-primary-container" : "text-[#1e1b13]"}`}>
                    {s.action}
                  </span>
                  <span className="font-mono text-[9px] xl:text-[10px] opacity-60 leading-snug">
                    {s.title}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
