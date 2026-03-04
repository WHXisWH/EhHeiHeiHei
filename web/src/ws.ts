import type { WsMessage } from "./types";

export function connectWs(onMessage: (msg: WsMessage) => void): WebSocket {
  const wsBase =
    import.meta.env.VITE_WS_BASE ??
    `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
  const ws = new WebSocket(`${wsBase}/ws/v1`);

  ws.addEventListener("message", (ev) => {
    try {
      onMessage(JSON.parse(String(ev.data)) as WsMessage);
    } catch {
      // ignore
    }
  });

  return ws;
}

export function subscribe(ws: WebSocket, agentIds: string[]) {
  ws.send(JSON.stringify({ type: "subscribe", payload: { agent_ids: agentIds } }));
}
