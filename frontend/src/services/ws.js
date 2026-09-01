import { getTokens } from "@/services/api";

/**
 * Opens a resilient WebSocket connection (auto-reconnect with backoff)
 * against a GanttFlow channel (project updates or task chat).
 * @param {string} path e.g. "projects/12" or "tasks/45/chat"
 * @param {(data: any) => void} onMessage
 */
export function connectSocket(path, onMessage) {
  let socket = null;
  let closedByClient = false;
  let attempt = 0;

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";

  function open() {
    const tokens = getTokens();
    const url = `${protocol}://${window.location.host}/ws/${path}/?token=${tokens?.access || ""}`;
    socket = new WebSocket(url);

    socket.onopen = () => {
      attempt = 0;
    };
    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch (e) {
        console.error("WS parse error", e);
      }
    };
    socket.onclose = () => {
      if (closedByClient) return;
      attempt += 1;
      const delay = Math.min(1000 * 2 ** attempt, 15000);
      setTimeout(open, delay);
    };
    socket.onerror = () => socket.close();
  }

  open();

  return {
    send(payload) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(payload));
      }
    },
    close() {
      closedByClient = true;
      socket?.close();
    },
  };
}
