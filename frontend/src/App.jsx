import { useState, useEffect, useRef, useCallback } from "react";
import Header from "./components/Header";
import ChatMessage from "./components/ChatMessage";
import CommandInput from "./components/CommandInput";
import { LeftPanel, RightPanel } from "./components/SidePanel";
import { useSSEChat } from "./hooks/useSSEChat";

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

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export default function App() {
  const [githubToken, setGithubToken] = useState(() => localStorage.getItem("github_token"));
  const [githubUser, setGithubUser] = useState(() => localStorage.getItem("github_user"));
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [tokenUsage, setTokenUsage] = useState({
    total_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    max_context_tokens: 0,
    cost_usd: null,
  });
  const bottomRef = useRef(null);
  const agentMsgIdRef = useRef(null);
  const chatHistoryRef = useRef([]);
  const assistantBufferRef = useRef("");

  // Handle OAuth callback: exchange code for token
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (!code) return;

    // Clean URL immediately
    window.history.replaceState({}, "", window.location.pathname);

    fetch(`${BACKEND_URL}/auth/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.access_token) {
          localStorage.setItem("github_token", data.access_token);
          localStorage.setItem("github_user", data.username);
          setGithubToken(data.access_token);
          setGithubUser(data.username);
        }
      })
      .catch(console.error);
  }, []);

  function handleLogout() {
    localStorage.removeItem("github_token");
    localStorage.removeItem("github_user");
    setGithubToken(null);
    setGithubUser(null);
  }

  const handleMessage = useCallback((data) => {
    const ts = timestamp();

    switch (data.type) {
      case "agent_step": {
        const id = agentMsgIdRef.current;
        const newStep = { step: data.step, action: data.action, title: data.title, content: "", done: false };
        setMessages((prev) => {
          const exists = prev.some((m) => m.id === id);
          if (exists) {
            return prev.map((m) => {
              if (m.id !== id) return m;
              // mark all previous steps as done, append new one
              const steps = m.steps.map((s) => ({ ...s, done: true }));
              return { ...m, steps: [...steps, newStep] };
            });
          }
          return [...prev, { id, role: "agent", steps: [newStep], timestamp: ts }];
        });
        break;
      }

      case "agent_stream": {
        const id = agentMsgIdRef.current;
        assistantBufferRef.current += data.delta || "";
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== id) return m;
            const steps = [...m.steps];
            const last = { ...steps[steps.length - 1], content: steps[steps.length - 1].content + (data.delta || "") };
            steps[steps.length - 1] = last;
            return { ...m, steps };
          })
        );
        break;
      }

      case "agent_step_done":
        break;

      case "agent_done": {
        const id = agentMsgIdRef.current;
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== id) return m;
            const steps = m.steps.map((s) => ({ ...s, done: true }));
            return { ...m, steps };
          })
        );
        // Append assistant response to conversation history
        if (assistantBufferRef.current) {
          chatHistoryRef.current.push({
            role: "assistant",
            content: assistantBufferRef.current,
          });
        }
        break;
      }

      case "agent_error":
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
        break;
    }
  }, []);

  const handleTokenUpdate = useCallback((payload) => {
    setTokenUsage((prev) => ({
      total_tokens: (prev.total_tokens || 0) + (payload.total_tokens || 0),
      prompt_tokens: (prev.prompt_tokens || 0) + (payload.prompt_tokens || 0),
      completion_tokens:
        (prev.completion_tokens || 0) + (payload.completion_tokens || 0),
      max_context_tokens: payload.max_context_tokens || prev.max_context_tokens,
      cost_usd:
        payload.cost_usd !== undefined
          ? (prev.cost_usd || 0) + payload.cost_usd
          : prev.cost_usd,
    }));
  }, []);

  const { streaming, send } = useSSEChat({
    onMessage: handleMessage,
    onTokenUpdate: handleTokenUpdate,
    githubToken,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(prompt) {
    const ts = timestamp();
    agentMsgIdRef.current = `agent-${Date.now()}`;
    assistantBufferRef.current = "";
    chatHistoryRef.current.push({ role: "user", content: prompt });
    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: "user", content: prompt, timestamp: ts },
    ]);
    send(chatHistoryRef.current);
  }

  const agentMsgExists = messages.some((m) => m.id === agentMsgIdRef.current && m.steps?.length > 0);

  if (!githubToken) {
    return (
      <div className="flex flex-col h-screen bg-background text-[#1e1b13] font-body items-center justify-center gap-8">
        <h1 className="text-5xl xl:text-6xl font-black uppercase tracking-tighter font-headline">
          PLUMBERITO
        </h1>
        <p className="font-mono text-sm uppercase tracking-widest opacity-50">
          DevOps & Infrastructure Assistant
        </p>
        <a
          href={`${BACKEND_URL}/auth/github`}
          className="border-4 border-[#1e1b13] bg-[#1e1b13] text-[#fff8ef] px-8 py-4 font-black uppercase tracking-tight text-lg hover:bg-[#fff8ef] hover:text-[#1e1b13] transition-colors brutalist-shadow"
        >
          Sign in with GitHub
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background text-[#1e1b13] font-body overflow-hidden">
      <Header tokenUsage={tokenUsage} streaming={streaming} githubUser={githubUser} onLogout={handleLogout} />

      <main className="flex-1 mt-16 xl:mt-20 2xl:mt-24 flex overflow-hidden bg-surface">
        <LeftPanel />

        <div className="flex-1 flex flex-col overflow-hidden">
          <section className="flex-1 overflow-y-auto p-8 xl:p-12 2xl:p-16 space-y-10 xl:space-y-12 2xl:space-y-16 scrollbar-thin">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {streaming && !agentMsgExists && (
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

          <CommandInput onSubmit={handleSubmit} disabled={streaming} />
        </div>

        <RightPanel />
      </main>

      <div className="fixed inset-0 pointer-events-none opacity-[0.03] mix-blend-multiply z-[100] hatch-pattern" />
    </div>
  );
}
