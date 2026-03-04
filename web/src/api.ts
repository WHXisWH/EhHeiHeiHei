import type { Agent, ConversationMessage, EventItem, SnsPost } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function seedDemo(): Promise<string[]> {
  const resp = await fetch(`${API_BASE}/internal/seed-demo`, { method: "POST" });
  if (!resp.ok) throw new Error(await resp.text());
  const data = (await resp.json()) as { created_agent_ids: string[] };
  return data.created_agent_ids;
}

export async function runTick(): Promise<void> {
  const resp = await fetch(`${API_BASE}/internal/tick`, { method: "POST" });
  if (!resp.ok) throw new Error(await resp.text());
}

export async function listAgents(): Promise<Agent[]> {
  const resp = await fetch(`${API_BASE}/api/v1/agents`);
  if (!resp.ok) throw new Error(await resp.text());
  const data = (await resp.json()) as { agents: Agent[] };
  return data.agents;
}

export async function sendMessage(agentId: string, content: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/v1/agents/${agentId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!resp.ok) throw new Error(await resp.text());
}

export async function listSnsPosts(): Promise<SnsPost[]> {
  const resp = await fetch(`${API_BASE}/api/v1/sns/posts?limit=50`);
  if (!resp.ok) throw new Error(await resp.text());
  const data = (await resp.json()) as { posts: SnsPost[] };
  return data.posts;
}

export async function listEvents(): Promise<EventItem[]> {
  const resp = await fetch(`${API_BASE}/api/v1/events?limit=200`);
  if (!resp.ok) throw new Error(await resp.text());
  const data = (await resp.json()) as { events: EventItem[] };
  return data.events;
}

export async function getConversations(agentId: string): Promise<ConversationMessage[]> {
  const resp = await fetch(`${API_BASE}/api/v1/agents/${agentId}/conversations?limit=20`);
  if (!resp.ok) throw new Error(await resp.text());
  const data = (await resp.json()) as { messages: ConversationMessage[] };
  return data.messages;
}
