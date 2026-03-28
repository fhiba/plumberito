import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

export function useWebSocket({ onMessage, onTokenUpdate }) {
  const ws = useRef(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      setConnected(true);
    };

    ws.current.onclose = () => {
      setConnected(false);
      reconnectTimeout.current = setTimeout(connect, 3000);
    };

    ws.current.onerror = () => {
      ws.current?.close();
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "token_usage" && onTokenUpdate) {
          onTokenUpdate(data.payload);
        } else if (onMessage) {
          onMessage(data);
        }
      } catch {
        if (onMessage) onMessage({ type: "text", content: event.data });
      }
    };
  }, [onMessage, onTokenUpdate]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);

  const send = useCallback((payload) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }, []);

  return { connected, send };
}
