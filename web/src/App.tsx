import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { listAgents, listEvents, listSnsPosts, runTick, seedDemo, sendMessage } from "./api";
import { connectWs, subscribe } from "./ws";
import type { Agent, AgentPosition, EventItem, SnsPost, WsMessage } from "./types";

const SHIBUYA_CENTER: [number, number] = [35.6595, 139.7005];

function upsertPosition(agent: Agent, pos: AgentPosition): Agent {
  return { ...agent, position: pos };
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string>("");
  const [snsPosts, setSnsPosts] = useState<SnsPost[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);

  const selectedAgent = useMemo(
    () => agents.find((a) => a.agent_id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );

  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.CircleMarker>>(new Map());
  const wsRef = useRef<WebSocket | null>(null);

  const agentNameById = useMemo(() => {
    const m = new Map<string, string>();
    for (const a of agents) m.set(a.agent_id, a.display_name);
    return m;
  }, [agents]);

  function pushEvent(item: EventItem) {
    setEvents((prev) => [item, ...prev].slice(0, 200));
  }

  async function refreshAgents() {
    const items = await listAgents();
    setAgents(items);
    if (!selectedAgentId && items[0]) setSelectedAgentId(items[0].agent_id);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      subscribe(wsRef.current, items.map((a) => a.agent_id));
    }

    // refresh feeds (best-effort)
    try {
      setSnsPosts(await listSnsPosts());
      setEvents(await listEvents());
    } catch (e) {
      setStatus(String(e));
    }
  }

  useEffect(() => {
    (async () => {
      await refreshAgents();
    })().catch((e) => setStatus(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (mapRef.current) return;
    const map = L.map("map").setView(SHIBUYA_CENTER, 16);
    mapRef.current = map;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    for (const a of agents) {
      if (!a.position) continue;
      const key = a.agent_id;
      const latlng: [number, number] = [a.position.lat, a.position.lon];
      const existing = markersRef.current.get(key);
      if (existing) existing.setLatLng(latlng);
      else {
        const marker = L.circleMarker(latlng, {
          radius: 8,
          color: "#2563eb",
          weight: 2,
          fillColor: "#60a5fa",
          fillOpacity: 0.9,
        }).addTo(map);
        marker.bindPopup(`${a.display_name} (${a.personality_type})`);
        markersRef.current.set(key, marker);
      }
    }
  }, [agents]);

  useEffect(() => {
    const ws = connectWs((msg: WsMessage) => {
      if (msg.type === "agent.position") {
        const pos: AgentPosition = {
          agent_id: msg.payload.agent_id,
          lat: msg.payload.lat,
          lon: msg.payload.lon,
          status: msg.payload.status,
          place_type: msg.payload.place_type,
          updated_at: msg.payload.ts,
        };
        setAgents((prev) =>
          prev.map((a) => (a.agent_id === msg.payload.agent_id ? upsertPosition(a, pos) : a)),
        );
        pushEvent({
          event_type: "ws.agent.position",
          agent_id: msg.payload.agent_id,
          payload: msg.payload,
          created_at: msg.payload.ts,
        });
      }
      if (msg.type === "agent.action") {
        pushEvent({
          event_type: "ws.agent.action",
          agent_id: msg.payload.agent_id,
          payload: msg.payload,
          created_at: new Date().toISOString(),
        });
      }
      if (msg.type === "agent.mood_change") {
        pushEvent({
          event_type: "ws.agent.mood_change",
          agent_id: msg.payload.agent_id,
          payload: msg.payload,
          created_at: msg.payload.ts,
        });
      }
      if (msg.type === "message.reply") {
        pushEvent({
          event_type: "ws.message.reply",
          agent_id: msg.payload.agent_id,
          payload: msg.payload,
          created_at: msg.payload.ts,
        });
      }
      if (msg.type === "sns.new_post") {
        setSnsPosts((prev) =>
          [
            {
              post_id: msg.payload.post_id,
              agent_id: msg.payload.agent_id,
              content: msg.payload.content,
              location: msg.payload.location ?? null,
              created_at: msg.payload.ts,
            },
            ...prev,
          ].slice(0, 50),
        );
        pushEvent({
          event_type: "ws.sns.new_post",
          agent_id: msg.payload.agent_id,
          payload: msg.payload,
          created_at: msg.payload.ts,
        });
      }
      if (msg.type === "world.tick") {
        pushEvent({
          event_type: "ws.world.tick",
          payload: msg.payload,
          created_at: msg.payload.completed_at,
        });
      }
      if (msg.type === "tick.error") setStatus(`${msg.payload.error}: ${msg.payload.message}`);
    });
    wsRef.current = ws;

    ws.addEventListener("open", () => {
      subscribe(ws, agents.map((a) => a.agent_id));
    });
    ws.addEventListener("close", () => setStatus("WS disconnected"));

    return () => {
      ws.close();
    };
    // connect once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    subscribe(ws, agents.map((a) => a.agent_id));
  }, [agents]);

  async function onSeed() {
    setStatus("");
    await seedDemo();
    await refreshAgents();
  }

  async function onTick() {
    setStatus("");
    await runTick();
    // best-effort refresh feeds
    try {
      setSnsPosts(await listSnsPosts());
      setEvents(await listEvents());
    } catch {
      // ignore
    }
  }

  async function onSend() {
    if (!selectedAgent) return;
    const trimmed = message.trim();
    if (!trimmed) return;
    setStatus("");
    await sendMessage(selectedAgent.agent_id, trimmed);
    setMessage("");
  }

  return (
    <div className="layout">
      <div className="panel">
        <h1>ParalleLife Web Observer</h1>
        <div className="row">
          <button onClick={onSeed}>Seed Demo (4 Agents)</button>
          <button onClick={onTick}>Run Tick</button>
          <button onClick={refreshAgents}>Refresh</button>
        </div>
        {status ? <div className="muted">{status}</div> : null}
        <div className="agents">
          {agents.map((a) => (
            <div
              key={a.agent_id}
              className={`agent ${a.agent_id === selectedAgentId ? "selected" : ""}`}
              onClick={() => setSelectedAgentId(a.agent_id)}
              role="button"
              tabIndex={0}
            >
              <div>
                <strong>{a.display_name}</strong> <span className="muted">({a.personality_type})</span>
              </div>
              <div className="muted">{a.occupation}</div>
              <div className="muted">mood {a.mood_score} · influence {a.influence_score}</div>
              {a.position ? (
                <div className="muted">{a.position.lat.toFixed(5)}, {a.position.lon.toFixed(5)} · {a.position.status}</div>
              ) : (
                <div className="muted">no position</div>
              )}
            </div>
          ))}
        </div>
        <hr />
        <div>
          <div className="muted">Send message to selected agent</div>
          <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} />
          <div className="row" style={{ marginTop: 8 }}>
            <button onClick={onSend} disabled={!selectedAgent}>
              Send
            </button>
          </div>
        </div>

        <div className="sectionTitle">SNS Feed</div>
        <div className="feed">
          {snsPosts.length ? (
            snsPosts.map((p) => (
              <div className="feedItem" key={p.post_id}>
                <div>
                  <strong>{agentNameById.get(p.agent_id) ?? p.agent_id.slice(0, 8)}</strong>{" "}
                  <span className="muted">{new Date(p.created_at).toLocaleString()}</span>
                </div>
                <div>{p.content}</div>
                {p.location ? (
                  <div className="muted">
                    {p.location.lat.toFixed(5)}, {p.location.lon.toFixed(5)}
                  </div>
                ) : null}
              </div>
            ))
          ) : (
            <div className="muted">No posts yet.</div>
          )}
        </div>

        <div className="sectionTitle">Event Stream</div>
        <div className="feed">
          {events.length ? (
            events.map((e, idx) => (
              <div className="feedItem" key={e.event_id ?? `${e.created_at}-${idx}`}>
                <div>
                  <strong>{e.event_type}</strong>{" "}
                  <span className="muted">{new Date(e.created_at).toLocaleString()}</span>
                </div>
                {e.agent_id ? <div className="muted">agent: {agentNameById.get(e.agent_id) ?? e.agent_id}</div> : null}
                <pre>{JSON.stringify(e.payload, null, 2)}</pre>
              </div>
            ))
          ) : (
            <div className="muted">No events yet.</div>
          )}
        </div>
      </div>
      <div id="map" className="map" />
    </div>
  );
}
