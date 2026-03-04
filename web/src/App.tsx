import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import {
  getConversations,
  listAgents,
  listEvents,
  listSnsPosts,
  runTick,
  seedDemo,
  sendMessage,
} from "./api";
import { connectWs, subscribe } from "./ws";
import type { Agent, AgentPosition, ConversationMessage, EventItem, SnsPost, WsMessage } from "./types";

const SHIBUYA_CENTER: [number, number] = [35.6595, 139.7005];

const MARKER_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c"];

function agentColor(index: number): string {
  return MARKER_COLORS[index % MARKER_COLORS.length];
}

function upsertPosition(agent: Agent, pos: AgentPosition): Agent {
  return { ...agent, position: pos };
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string>("");
  const [wsConnected, setWsConnected] = useState(false);
  const [snsPosts, setSnsPosts] = useState<SnsPost[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [conversations, setConversations] = useState<ConversationMessage[]>([]);
  const [autoTick, setAutoTick] = useState(false);
  const [tickInterval, setTickInterval] = useState(30);
  const [activeTab, setActiveTab] = useState<"chat" | "sns" | "events">("chat");

  const selectedAgent = useMemo(
    () => agents.find((a) => a.agent_id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );

  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.CircleMarker>>(new Map());
  const wsRef = useRef<WebSocket | null>(null);
  const agentIndexRef = useRef<Map<string, number>>(new Map());

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
    try {
      setSnsPosts(await listSnsPosts());
      setEvents(await listEvents());
    } catch (e) {
      setStatus(String(e));
    }
  }

  // Initial load
  useEffect(() => {
    refreshAgents().catch((e) => setStatus(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch conversations when selected agent changes
  useEffect(() => {
    if (!selectedAgentId) return;
    setConversations([]);
    getConversations(selectedAgentId)
      .then(setConversations)
      .catch(() => {/* best-effort */});
  }, [selectedAgentId]);

  // Auto-tick
  useEffect(() => {
    if (!autoTick) return;
    const id = setInterval(() => {
      onTick();
    }, tickInterval * 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoTick, tickInterval]);

  // Map init
  useEffect(() => {
    if (mapRef.current) return;
    const map = L.map("map").setView(SHIBUYA_CENTER, 16);
    mapRef.current = map;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
  }, []);

  // Sync markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    agents.forEach((a, idx) => {
      if (!agentIndexRef.current.has(a.agent_id)) {
        agentIndexRef.current.set(a.agent_id, idx);
      }
    });

    for (const a of agents) {
      if (!a.position) continue;
      const key = a.agent_id;
      const latlng: [number, number] = [a.position.lat, a.position.lon];
      const color = agentColor(agentIndexRef.current.get(key) ?? 0);
      const isSelected = key === selectedAgentId;
      const existing = markersRef.current.get(key);
      if (existing) {
        existing.setLatLng(latlng);
        existing.setStyle({
          radius: isSelected ? 12 : 8,
          weight: isSelected ? 3 : 2,
        });
      } else {
        const marker = L.circleMarker(latlng, {
          radius: isSelected ? 12 : 8,
          color,
          weight: isSelected ? 3 : 2,
          fillColor: color,
          fillOpacity: 0.85,
        }).addTo(map);
        marker.bindPopup(`${a.display_name} (${a.personality_type})`);
        marker.on("click", () => {
          setSelectedAgentId(key);
          setActiveTab("chat");
        });
        markersRef.current.set(key, marker);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agents, selectedAgentId]);

  // WebSocket
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
        const reply: ConversationMessage = {
          message_id: `ws-${Date.now()}`,
          agent_id: msg.payload.agent_id,
          role: "assistant",
          content: msg.payload.content,
          processed: true,
          importance: 0,
          created_at: msg.payload.ts,
        };
        setConversations((prev) => [...prev, reply]);
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
      setWsConnected(true);
      subscribe(ws, agents.map((a) => a.agent_id));
    });
    ws.addEventListener("close", () => setWsConnected(false));

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
    try {
      await runTick();
      setSnsPosts(await listSnsPosts());
      setEvents(await listEvents());
    } catch (e) {
      setStatus(String(e));
    }
  }

  async function onSend() {
    if (!selectedAgent) return;
    const trimmed = message.trim();
    if (!trimmed) return;
    setStatus("");
    const userMsg: ConversationMessage = {
      message_id: `local-${Date.now()}`,
      agent_id: selectedAgent.agent_id,
      role: "user",
      content: trimmed,
      processed: false,
      importance: 0,
      created_at: new Date().toISOString(),
    };
    setConversations((prev) => [...prev, userMsg]);
    setMessage("");
    try {
      await sendMessage(selectedAgent.agent_id, trimmed);
    } catch (e) {
      setStatus(String(e));
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSend();
    }
  }

  return (
    <div className="layout">
      <div className="panel">
        {/* Header */}
        <div className="panelHeader">
          <h1>ParalleLife</h1>
          <span className={`wsStatus ${wsConnected ? "wsOn" : "wsOff"}`}>
            {wsConnected ? "WS ●" : "WS ○"}
          </span>
        </div>

        {/* Controls */}
        <div className="row">
          <button onClick={onSeed}>Seed</button>
          <button onClick={onTick} title="Run one world tick">Tick</button>
          <button
            onClick={() => setAutoTick((v) => !v)}
            className={autoTick ? "btnActive" : ""}
            title="Auto-tick every N seconds"
          >
            {autoTick ? "⏸ Auto" : "▶ Auto"}
          </button>
          {autoTick && (
            <select
              value={tickInterval}
              onChange={(e) => setTickInterval(Number(e.target.value))}
              style={{ fontSize: 12 }}
            >
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>60s</option>
            </select>
          )}
          <button onClick={refreshAgents}>↺</button>
        </div>
        {status ? <div className="statusError">{status}</div> : null}

        {/* Agent list */}
        <div className="agents">
          {agents.map((a, idx) => {
            const color = agentColor(idx);
            return (
              <div
                key={a.agent_id}
                className={`agent ${a.agent_id === selectedAgentId ? "selected" : ""}`}
                onClick={() => {
                  setSelectedAgentId(a.agent_id);
                  setActiveTab("chat");
                }}
                role="button"
                tabIndex={0}
              >
                <div className="agentHeader">
                  <span className="agentDot" style={{ background: color }} />
                  <strong>{a.display_name}</strong>
                  <span className="muted">({a.personality_type})</span>
                </div>
                <div className="muted">{a.occupation}</div>
                <div className="agentStats">
                  <span>情绪 {a.mood_score}</span>
                  <div className="moodBar">
                    <div
                      className="moodFill"
                      style={{
                        width: `${Math.max(0, Math.min(100, (a.mood_score + 10) * 5))}%`,
                        background: a.mood_score >= 0 ? "#16a34a" : "#dc2626",
                      }}
                    />
                  </div>
                  <span>影响 {a.influence_score}</span>
                </div>
                {a.position ? (
                  <div className="muted">
                    {a.position.status} · {a.position.place_type}
                  </div>
                ) : (
                  <div className="muted">no position</div>
                )}
              </div>
            );
          })}
        </div>

        {/* Tabs */}
        {agents.length > 0 && (
          <>
            <div className="tabs">
              <button
                className={`tab ${activeTab === "chat" ? "tabActive" : ""}`}
                onClick={() => setActiveTab("chat")}
              >
                对话
              </button>
              <button
                className={`tab ${activeTab === "sns" ? "tabActive" : ""}`}
                onClick={() => setActiveTab("sns")}
              >
                SNS {snsPosts.length > 0 ? `(${snsPosts.length})` : ""}
              </button>
              <button
                className={`tab ${activeTab === "events" ? "tabActive" : ""}`}
                onClick={() => setActiveTab("events")}
              >
                Events {events.length > 0 ? `(${events.length})` : ""}
              </button>
            </div>

            {/* Chat tab */}
            {activeTab === "chat" && (
              <div className="chatPanel">
                {selectedAgent ? (
                  <>
                    <div className="chatTitle">
                      与 <strong>{selectedAgent.display_name}</strong> 对话
                    </div>
                    <div className="chatMessages">
                      {conversations.length === 0 && (
                        <div className="muted" style={{ padding: 8 }}>
                          暂无对话记录。发送消息或 Run Tick 后 agent 会回应。
                        </div>
                      )}
                      {conversations.map((m) => (
                        <div
                          key={m.message_id}
                          className={`chatMsg ${m.role === "user" ? "chatMsgUser" : "chatMsgAgent"}`}
                        >
                          <div className="chatMsgContent">{m.content}</div>
                          <div className="muted chatMsgTime">
                            {new Date(m.created_at).toLocaleTimeString()}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="chatInput">
                      <textarea
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        rows={2}
                        placeholder="发送消息… (Cmd+Enter 发送)"
                      />
                      <button onClick={onSend} disabled={!message.trim()}>
                        发送
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="muted" style={{ padding: 8 }}>
                    请先点击左侧 Agent。
                  </div>
                )}
              </div>
            )}

            {/* SNS tab */}
            {activeTab === "sns" && (
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
            )}

            {/* Events tab */}
            {activeTab === "events" && (
              <div className="feed">
                {events.length ? (
                  events.map((e, idx) => (
                    <div className="feedItem" key={e.event_id ?? `${e.created_at}-${idx}`}>
                      <div>
                        <strong>{e.event_type}</strong>{" "}
                        <span className="muted">{new Date(e.created_at).toLocaleString()}</span>
                      </div>
                      {e.agent_id ? (
                        <div className="muted">
                          agent: {agentNameById.get(e.agent_id) ?? e.agent_id}
                        </div>
                      ) : null}
                      <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                    </div>
                  ))
                ) : (
                  <div className="muted">No events yet.</div>
                )}
              </div>
            )}
          </>
        )}
      </div>
      <div id="map" className="map" />
    </div>
  );
}
