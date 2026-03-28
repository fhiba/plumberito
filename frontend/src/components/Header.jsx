export default function Header({ tokenUsage, streaming }) {
  const total = tokenUsage?.total_tokens ?? 0;
  const prompt = tokenUsage?.prompt_tokens ?? 0;
  const completion = tokenUsage?.completion_tokens ?? 0;
  const cost = tokenUsage?.cost_usd ?? null;

  return (
    <nav className="fixed top-0 w-full border-b-4 border-[#1e1b13] z-50 bg-[#fff8ef] flex justify-between items-center h-16 xl:h-20 2xl:h-24 px-6 xl:px-10 2xl:px-16">
      <span className="text-2xl xl:text-3xl 2xl:text-4xl 3xl:text-5xl font-black uppercase tracking-tighter text-[#1e1b13] font-headline">
        PLUMBERITO
      </span>

      <div className="flex items-center gap-4 xl:gap-6">
        {/* SSE activity indicator */}
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 xl:w-2.5 xl:h-2.5 2xl:w-3 2xl:h-3 transition-colors duration-300 ${
              streaming ? "bg-[#1bff00] animate-pulse" : "bg-[#CC0000]"
            }`}
          />
          <span className={`font-mono text-[10px] xl:text-xs 2xl:text-sm uppercase tracking-widest ${streaming ? "text-[#1bff00]" : "text-[#CC0000]"}`}>
            {streaming ? "LIVE" : "STANDBY"}
          </span>
        </div>

        {/* Token counter */}
        <div className="flex items-center gap-3 border-2 border-[#1e1b13] px-3 xl:px-4 py-1.5 xl:py-2 bg-surface-container">
          <span className="material-symbols-outlined text-base xl:text-xl 2xl:text-2xl text-[#CC0000]">
            data_usage
          </span>
          <div className="flex flex-col items-end">
            <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs uppercase tracking-widest text-secondary">
              TOKENS / OPENROUTER
            </span>
            <div className="flex items-baseline gap-3">
              <span className="font-headline font-black text-sm xl:text-base 2xl:text-lg tracking-tighter text-[#1e1b13]">
                {total.toLocaleString()}
              </span>
              <span className="font-mono text-[9px] xl:text-[10px] 2xl:text-xs opacity-50">
                ↑{prompt.toLocaleString()} ↓{completion.toLocaleString()}
              </span>
              {cost !== null && (
                <span className="font-mono text-[10px] xl:text-xs 2xl:text-sm text-[#CC0000] font-bold">
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
