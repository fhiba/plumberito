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

const LOGOS = {
  github: (
    <svg viewBox="0 0 24 24" className="w-5 h-5 shrink-0" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
    </svg>
  ),
  deploy: (
    <svg viewBox="0 0 24 24" className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
    </svg>
  ),
  sentry: (
    <svg viewBox="0 0 72 66" className="w-5 h-5 shrink-0" fill="currentColor">
      <path d="M29.976 3.027a5.304 5.304 0 0 0-9.192 0L.79 40.65a5.25 5.25 0 0 0 4.596 7.782h7.008a33.108 33.108 0 0 1 4.764-11.478 25.044 25.044 0 0 0-5.136.696l8.022-13.914a25.794 25.794 0 0 1 10.638 20.694c0 1.398-.114 2.772-.33 4.002h8.172a33.54 33.54 0 0 0 .33-4.002A34.02 34.02 0 0 0 29.976 3.027zm32.04 37.623L46.386 14.157a5.304 5.304 0 0 0-9.192 0l-2.196 3.804a42.876 42.876 0 0 1 11.244 26.73h-5.07a37.95 37.95 0 0 0-5.07-17.49l-4.374 7.578a26.058 26.058 0 0 1 3.126 9.912H5.388A5.25 5.25 0 0 0 9.984 55.5h52.032a5.25 5.25 0 0 0 4.596-7.782z"/>
    </svg>
  ),
};

const ARTIFACT_STYLE = {
  github: { bg: "#1e1b13", text: "#fff8ef", border: "#1e1b13" },
  deploy: { bg: "#fff8ef", text: "#1e1b13", border: "#1e1b13" },
  sentry: { bg: "#362d59", text: "#fff8ef", border: "#362d59" },
};

function ArtifactCard({ kind, label, url }) {
  const style = ARTIFACT_STYLE[kind] || ARTIFACT_STYLE.deploy;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2.5 px-3 py-2.5 border-2 hover:opacity-80 transition-opacity"
      style={{ backgroundColor: style.bg, borderColor: style.border, color: style.text,
               animation: "stampIn 180ms cubic-bezier(0.22, 1, 0.36, 1) both" }}
    >
      <span style={{ color: style.text }}>{LOGOS[kind]}</span>
      <div className="flex flex-col min-w-0">
        <span className="font-mono text-[8px] uppercase tracking-widest opacity-50">
          {kind === "github" ? "REPO" : kind === "deploy" ? "LIVE URL" : "MONITORING"}
        </span>
        <span className="font-mono text-[9px] xl:text-[10px] font-bold truncate">{label}</span>
      </div>
      <svg viewBox="0 0 24 24" className="w-3 h-3 shrink-0 ml-auto opacity-40" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M7 17L17 7M17 7H7M17 7v10"/>
      </svg>
    </a>
  );
}

export function RightPanel({ artifacts = [] }) {
  return (
    <aside className={`${panelBase} border-l-4 border-[#1e1b13]`}>
      <div className="border-b-2 border-[#1e1b13] border-opacity-30 px-4 xl:px-5 2xl:px-6 py-3 xl:py-4">
        <div className="font-label font-black text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-[0.25em] text-primary-container">
          ARTIFACTS
        </div>
      </div>

      <div className="px-3 xl:px-4 py-3 flex flex-col gap-2">
        {artifacts.length === 0 ? (
          <div className="font-mono text-[9px] xl:text-[10px] opacity-20 uppercase tracking-widest pt-1">
            IDLE
          </div>
        ) : (
          artifacts.map((a) => (
            <ArtifactCard key={a.url} {...a} />
          ))
        )}
      </div>
    </aside>
  );
}
