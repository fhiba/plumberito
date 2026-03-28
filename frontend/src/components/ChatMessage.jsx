import { useState } from "react";
import ReactMarkdown from "react-markdown";

const HARDCODED_USER = "COMMANDER";

function MarkdownContent({ content, className = "" }) {
  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      <ReactMarkdown
        components={{
          pre({ children }) {
            const child = Array.isArray(children) ? children[0] : children;
            const lang = /language-(\w+)/.exec(child?.props?.className || "")?.[1] || "";
            return (
              <div className="bg-[#1e1b13] p-4 xl:p-5 2xl:p-6 text-primary font-mono text-xs xl:text-sm leading-relaxed overflow-x-auto mt-3 not-prose">
                <div className="text-white mb-2 opacity-50 uppercase text-[10px] xl:text-xs tracking-widest border-b border-white border-opacity-20 pb-1">
                  {lang || "code"}
                </div>
                <pre className="whitespace-pre-wrap break-words text-[#fff8ef]">{child?.props?.children ?? children}</pre>
              </div>
            );
          },
          code({ className, children, ...props }) {
            return (
              <code
                className="bg-[#1e1b13] bg-opacity-15 text-[#1e1b13] font-mono text-[0.85em] px-1 py-0.5 rounded-sm"
                {...props}
              >
                {children}
              </code>
            );
          },
          p({ children }) {
            return (
              <p className="text-sm xl:text-base 2xl:text-lg font-medium leading-relaxed mb-2 last:mb-0">
                {children}
              </p>
            );
          },
          h1({ children }) {
            return (
              <h1 className="font-headline font-black text-xl xl:text-2xl uppercase tracking-tighter mb-3 leading-none">
                {children}
              </h1>
            );
          },
          h2({ children }) {
            return (
              <h2 className="font-headline font-black text-lg xl:text-xl uppercase tracking-tighter mb-2 leading-none">
                {children}
              </h2>
            );
          },
          h3({ children }) {
            return (
              <h3 className="font-headline font-bold text-base xl:text-lg uppercase tracking-tight mb-2 leading-none">
                {children}
              </h3>
            );
          },
          ul({ children }) {
            return <ul className="list-disc list-inside space-y-1 my-2 text-sm xl:text-base">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal list-inside space-y-1 my-2 text-sm xl:text-base">{children}</ol>;
          },
          li({ children }) {
            return <li className="font-medium leading-relaxed">{children}</li>;
          },
          strong({ children }) {
            return <strong className="font-black">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic opacity-80">{children}</em>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-[#1e1b13] border-opacity-40 pl-3 my-2 opacity-70">
                {children}
              </blockquote>
            );
          },
          hr() {
            return <hr className="border-[#1e1b13] border-opacity-20 my-3" />;
          },
        }}
      >
        {content || ""}
      </ReactMarkdown>
    </div>
  );
}

function CollapsedStep({ step, expanded, onToggle }) {
  return (
    <div className="border-b border-[#1e1b13] border-opacity-10 last:border-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 py-2 xl:py-2.5 px-1 text-left hover:bg-[#1e1b13] hover:bg-opacity-5 transition-none group"
      >
        <span className="bg-[#1e1b13] bg-opacity-20 text-[#1e1b13] opacity-40 px-1.5 py-0.5 text-[9px] xl:text-[10px] 2xl:text-xs font-black uppercase tracking-tighter font-label shrink-0">
          {step.action}
        </span>
        <span className="font-headline font-bold text-xs xl:text-sm 2xl:text-base uppercase tracking-tight text-[#1e1b13] opacity-40 flex-1 truncate">
          {step.title}
        </span>
        <span className="material-symbols-outlined text-sm xl:text-base opacity-30 group-hover:opacity-50 shrink-0">
          {expanded ? "expand_less" : "expand_more"}
        </span>
      </button>
      {expanded && (
        <div className="px-1 pb-3 xl:pb-4 pt-1 opacity-50">
          <MarkdownContent content={step.content} />
        </div>
      )}
    </div>
  );
}

function AgentMessage({ message }) {
  const [expandedSteps, setExpandedSteps] = useState(new Set());

  const steps = message.steps ?? [];
  const doneSteps = steps.filter((s) => s.done);
  const activeStep = steps.find((s) => !s.done);

  function toggleStep(idx) {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  return (
    <div className="flex flex-col max-w-3xl xl:max-w-4xl 2xl:max-w-5xl 3xl:max-w-6xl">
      <div className="flex items-center gap-2 mb-3 xl:mb-4">
        <span className="bg-primary-container text-white px-2 py-0.5 text-[10px] xl:text-xs 2xl:text-sm font-black uppercase tracking-tighter font-label">
          DIRECTIVE
        </span>
        <span className="text-[10px] xl:text-xs font-mono opacity-50">{message.timestamp}</span>
        {activeStep && (
          <span className="text-[10px] xl:text-xs font-mono text-primary-container animate-pulse">▋</span>
        )}
      </div>

      <div className="bg-surface-container border-2 border-[#1e1b13] brutalist-shadow overflow-hidden">
        {doneSteps.length > 0 && (
          <div className="px-4 xl:px-5 2xl:px-6 pt-3 xl:pt-4 pb-1">
            {doneSteps.map((step, i) => (
              <CollapsedStep
                key={i}
                step={step}
                expanded={expandedSteps.has(i)}
                onToggle={() => toggleStep(i)}
              />
            ))}
          </div>
        )}

        {activeStep && (
          <div className={`p-5 xl:p-6 2xl:p-8 ${doneSteps.length > 0 ? "border-t-2 border-[#1e1b13] border-opacity-10" : ""}`}>
            <div className="flex items-center gap-2 mb-3 xl:mb-4">
              <span className="bg-[#1e1b13] text-[#fff8ef] px-1.5 py-0.5 text-[9px] xl:text-[10px] 2xl:text-xs font-black uppercase tracking-tighter font-label">
                {activeStep.action}
              </span>
            </div>
            {activeStep.title && (
              <h2 className="font-headline font-black text-xl xl:text-2xl 2xl:text-3xl uppercase tracking-tighter mb-3 xl:mb-4 leading-none">
                {activeStep.title}
              </h2>
            )}
            <MarkdownContent content={activeStep.content} />
          </div>
        )}

        {!activeStep && doneSteps.length > 0 && (() => {
          const last = doneSteps[doneSteps.length - 1];
          const lastIdx = doneSteps.length - 1;
          if (expandedSteps.has(lastIdx)) return null;
          return (
            <div className={`p-5 xl:p-6 2xl:p-8 ${doneSteps.length > 1 ? "border-t-2 border-[#1e1b13] border-opacity-10" : ""}`}>
              <MarkdownContent content={last.content} />
            </div>
          );
        })()}
      </div>
    </div>
  );
}

export default function ChatMessage({ message }) {
  if (message.role === "user") {
    return (
      <div className="flex flex-col items-end animate-slide-in-right">
        <div className="flex items-center gap-2 mb-3 xl:mb-4 flex-row-reverse">
          <span className="bg-[#1e1b13] text-[#fff8ef] px-2 py-0.5 text-[10px] xl:text-xs 2xl:text-sm font-black uppercase tracking-tighter font-label">
            {HARDCODED_USER}
          </span>
          <span className="text-[10px] xl:text-xs font-mono opacity-50">{message.timestamp}</span>
        </div>
        <div className="bg-surface p-5 xl:p-6 2xl:p-7 border-2 border-[#1e1b13] brutalist-shadow-sm max-w-xl xl:max-w-2xl 2xl:max-w-3xl text-right">
          <MarkdownContent content={message.content} className="text-right [&_p]:text-right [&_ul]:text-left [&_ol]:text-left" />
        </div>
      </div>
    );
  }

  if (message.role === "system") {
    return (
      <div className="flex flex-col max-w-3xl xl:max-w-4xl 2xl:max-w-5xl">
        <div className="flex items-center gap-2 mb-3 xl:mb-4">
          <span className="bg-primary-container text-white px-2 py-0.5 text-[10px] xl:text-xs 2xl:text-sm font-black uppercase tracking-tighter font-label">
            SYSTEM_OUTPUT
          </span>
          <span className="text-[10px] xl:text-xs font-mono opacity-50">{message.timestamp}</span>
        </div>
        <div className="bg-surface-container p-5 xl:p-6 2xl:p-8 border-2 border-[#1e1b13] brutalist-shadow">
          <MarkdownContent content={message.content} className="opacity-70" />
        </div>
      </div>
    );
  }

  return <AgentMessage message={message} />;
}
