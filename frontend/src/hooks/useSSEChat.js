import { useCallback, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { createMockSSEStream } from "../mocks/mockSSEStream";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
const IS_MOCK = import.meta.env.VITE_MOCK === "true";
const IS_DEV = import.meta.env.DEV;

function logEvent(data) {
  if (!IS_DEV) return;
  const color = data.type === "agent_stream" ? "#888" : "#1bff00";
  console.log(`%c[SSE] ${data.type}`, `color: ${color}; font-weight: bold;`, data);
}

async function getSSEReader(messages, signal, githubToken) {
  if (IS_MOCK) {
    return createMockSSEStream(messages[messages.length - 1]?.content || "").getReader();
  }
  const body = { messages };
  if (githubToken) body.github_token = githubToken;
  const response = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.body.getReader();
}

export function useSSEChat({ onMessage, onTokenUpdate, githubToken }) {
  const abortRef = useRef(null);

  const { mutate, isPending } = useMutation({
    mutationFn: async (messages) => {
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      const reader = await getSSEReader(messages, abortRef.current.signal, githubToken);
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw || raw === "[DONE]") continue;
          try {
            const data = JSON.parse(raw);
            logEvent(data);
            if (data.type === "token_usage") {
              onTokenUpdate?.(data.payload);
            } else {
              onMessage?.(data);
            }
          } catch {
            // malformed chunk — skip
          }
        }
      }
    },
    onError: (error) => {
      if (error.name === "AbortError") return;
      onMessage?.({ type: "agent_error", message: error.message });
    },
  });

  const send = useCallback((prompt) => mutate(prompt), [mutate]);

  return { streaming: isPending, send };
}
