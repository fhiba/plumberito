export default function Header({ tokenUsage, connected }) {
  const total = tokenUsage?.total_tokens ?? 0;
  const prompt = tokenUsage?.prompt_tokens ?? 0;
  const completion = tokenUsage?.completion_tokens ?? 0;
  const cost = tokenUsage?.cost_usd ?? null;

  return (
    <nav className="fixed top-0 w-full border-b-4 border-[#1e1b13] z-50 bg-[#fff8ef] flex justify-between items-center h-16 px-6">
      <span className="text-2xl font-black uppercase tracking-tighter text-[#1e1b13] font-headline">
        PLUMBERITO
      </span>

      <div className="flex items-center gap-4">
        {/* Connection indicator */}
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 ${connected ? "bg-[#1bff00]" : "bg-[#CC0000]"}`}
          />
          <span className="font-mono text-[10px] uppercase tracking-widest opacity-60">
            {connected ? "ONLINE" : "OFFLINE"}
          </span>
        </div>

        {/* Token counter */}
        <div className="flex items-center gap-3 border-2 border-[#1e1b13] px-3 py-1.5 bg-surface-container">
          <span className="material-symbols-outlined text-base text-[#CC0000]">
            data_usage
          </span>
          <div className="flex flex-col items-end">
            <span className="font-mono text-[9px] uppercase tracking-widest text-secondary">
              TOKENS / OPENROUTER
            </span>
            <div className="flex items-baseline gap-3">
              <span className="font-headline font-black text-sm tracking-tighter text-[#1e1b13]">
                {total.toLocaleString()}
              </span>
              <span className="font-mono text-[9px] opacity-50">
                ↑{prompt.toLocaleString()} ↓{completion.toLocaleString()}
              </span>
              {cost !== null && (
                <span className="font-mono text-[10px] text-[#CC0000] font-bold">
                  ${cost.toFixed(4)}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
