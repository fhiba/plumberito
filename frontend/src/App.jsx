import { useState, useEffect, useRef, useCallback } from "react";
import Header from "./components/Header";
import ChatMessage from "./components/ChatMessage";
import CommandInput from "./components/CommandInput";
import { LeftPanel, RightPanel } from "./components/SidePanel";
import { useWebSocket } from "./hooks/useWebSocket";

function timestamp() {
  return new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

const INITIAL_MESSAGE = {
  id: "init",
  role: "system",
  content:
    "Initialization complete. Plumberito agent is standing by. Enter a prompt to begin deployment.",
  timestamp: timestamp(),
};

export default function App() {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [tokenUsage, setTokenUsage] = useState({
    total_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    cost_usd: null,
  });
  const [agentBusy, setAgentBusy] = useState(false);
  const bottomRef = useRef(null);
  const streamingIdRef = useRef(null);

  const handleMessage = useCallback((data) => {
    const ts = timestamp();

    switch (data.type) {
      case "agent_start":
        setAgentBusy(true);
        break;

      case "agent_step": {
        const id = `step-${Date.now()}`;
        streamingIdRef.current = id;
        setMessages((prev) => [
          ...prev,
          {
            id,
            role: "agent",
            step: data.step,
            action: data.action,
            title: data.title,
            content: data.content || "",
            streaming: true,
            timestamp: ts,
          },
        ]);
        break;
      }

      case "agent_stream": {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === streamingIdRef.current
              ? { ...m, content: m.content + (data.delta || "") }
              : m
          )
        );
        break;
      }

      case "agent_step_done": {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === streamingIdRef.current ? { ...m, streaming: false } : m
          )
        );
        streamingIdRef.current = null;
        break;
      }

      case "agent_done":
        setAgentBusy(false);
        break;

      case "agent_error":
        setAgentBusy(false);
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: "system",
            content: `ERROR: ${data.message || "Unknown error occurred."}`,
            timestamp: ts,
          },
        ]);
        break;

      default:
        // Unknown message type — ignore
        break;
    }
  }, []);

  const handleTokenUpdate = useCallback((payload) => {
    setTokenUsage((prev) => ({
      total_tokens: (prev.total_tokens || 0) + (payload.total_tokens || 0),
      prompt_tokens: (prev.prompt_tokens || 0) + (payload.prompt_tokens || 0),
      completion_tokens:
        (prev.completion_tokens || 0) + (payload.completion_tokens || 0),
      cost_usd:
        payload.cost_usd !== undefined
          ? (prev.cost_usd || 0) + payload.cost_usd
          : prev.cost_usd,
    }));
  }, []);

  const { connected, send } = useWebSocket({
    onMessage: handleMessage,
    onTokenUpdate: handleTokenUpdate,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(prompt) {
    const ts = timestamp();

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: prompt,
        timestamp: ts,
      },
    ]);

    const sent = send({ type: "prompt", content: prompt });

    if (!sent) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "system",
          content: "ERROR: Not connected to backend. Retrying...",
          timestamp: ts,
        },
      ]);
    } else {
      setAgentBusy(true);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-background text-[#1e1b13] font-body overflow-hidden">
      <Header tokenUsage={tokenUsage} connected={connected} />

      <main className="flex-1 mt-16 flex overflow-hidden bg-surface">
        <LeftPanel />

        {/* Center: chat + input */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <section className="flex-1 overflow-y-auto p-8 space-y-10 scrollbar-thin">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {agentBusy && !streamingIdRef.current && (
              <div className="flex flex-col max-w-3xl">
                <div className="flex items-center gap-2 mb-3">
                  <span className="bg-primary-container text-white px-2 py-0.5 text-[10px] font-black uppercase tracking-tighter font-label">
                    PROCESSING
                  </span>
                </div>
                <div className="bg-surface-container p-5 border-2 border-[#1e1b13] brutalist-shadow">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-primary-container animate-pulse">
                      ▋▋▋
                    </span>
                    <span className="font-mono text-xs opacity-50 uppercase tracking-widest">
                      Agent executing...
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </section>

          <CommandInput onSubmit={handleSubmit} disabled={agentBusy} />
        </div>

        <RightPanel />
      </main>

      {/* Overlay noise */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] mix-blend-multiply z-[100] hatch-pattern" />
    </div>
  );
}
