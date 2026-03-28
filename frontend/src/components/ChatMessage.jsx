const HARDCODED_USER = "COMMANDER";

function CodeBlock({ code, lang }) {
  return (
    <div className="bg-[#1e1b13] p-4 text-primary font-mono text-xs leading-relaxed overflow-x-auto mt-3">
      <div className="text-white mb-2 opacity-50 uppercase text-[10px] tracking-widest border-b border-white border-opacity-20 pb-1">
        {lang || "code"}
      </div>
      <pre className="whitespace-pre-wrap break-words">{code}</pre>
    </div>
  );
}

function parseContent(content) {
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: "code", lang: match[1], value: match[2].trim() });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: "text", value: content.slice(lastIndex) });
  }

  return parts;
}

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const isStreaming = message.streaming === true;

  const parts = parseContent(message.content || "");

  if (isUser) {
    return (
      <div className="flex flex-col items-end animate-slide-in-right">
        <div className="flex items-center gap-2 mb-3 flex-row-reverse">
          <span className="bg-[#1e1b13] text-[#fff8ef] px-2 py-0.5 text-[10px] font-black uppercase tracking-tighter font-label">
            {HARDCODED_USER}
          </span>
          <span className="text-[10px] font-mono opacity-50">{message.timestamp}</span>
        </div>
        <div className="bg-surface p-5 border-2 border-[#1e1b13] brutalist-shadow-sm max-w-xl text-right">
          <p className="text-sm font-bold break-words whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  if (isSystem) {
    return (
      <div className="flex flex-col max-w-3xl">
        <div className="flex items-center gap-2 mb-3">
          <span className="bg-primary-container text-white px-2 py-0.5 text-[10px] font-black uppercase tracking-tighter font-label">
            SYSTEM_OUTPUT
          </span>
          <span className="text-[10px] font-mono opacity-50">{message.timestamp}</span>
        </div>
        <div className="bg-surface-container p-5 border-2 border-[#1e1b13] brutalist-shadow">
          <p className="text-sm font-medium leading-relaxed opacity-70">{message.content}</p>
        </div>
      </div>
    );
  }

  // Agent message
  return (
    <div className="flex flex-col max-w-3xl">
      <div className="flex items-center gap-2 mb-3">
        <span className="bg-primary-container text-white px-2 py-0.5 text-[10px] font-black uppercase tracking-tighter font-label">
          {message.step ? `STEP_${String(message.step).padStart(2, "0")}` : "DIRECTIVE"}
        </span>
        {message.action && (
          <span className="bg-[#1e1b13] text-[#fff8ef] px-2 py-0.5 text-[10px] font-black uppercase tracking-tighter font-label">
            {message.action}
          </span>
        )}
        <span className="text-[10px] font-mono opacity-50">{message.timestamp}</span>
        {isStreaming && (
          <span className="text-[10px] font-mono text-primary-container animate-pulse">
            ▋
          </span>
        )}
      </div>
      <div className="bg-surface-container p-5 border-2 border-[#1e1b13] brutalist-shadow">
        {message.title && (
          <h2 className="font-headline font-black text-xl uppercase tracking-tighter mb-3 leading-none">
            {message.title}
          </h2>
        )}
        {parts.map((part, i) =>
          part.type === "code" ? (
            <CodeBlock key={i} code={part.value} lang={part.lang} />
          ) : (
            <p key={i} className="text-sm font-medium leading-relaxed">
              {part.value}
            </p>
          )
        )}
      </div>
    </div>
  );
}
