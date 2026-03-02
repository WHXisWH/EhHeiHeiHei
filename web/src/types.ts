export type Agent = {
  agent_id: string;
  display_name: string;
  personality_type: string;
  occupation: string;
  mood_score: number;
  influence_score: number;
  created_at: string;
  position?: AgentPosition | null;
};

export type AgentPosition = {
  agent_id: string;
  lat: number;
  lon: number;
  status: string;
  place_type: string;
  updated_at: string;
};

export type WsAgentPosition = {
  agent_id: string;
  lat: number;
  lon: number;
  status: string;
  place_type: string;
  ts: string;
};

export type SnsPost = {
  post_id: string;
  agent_id: string;
  content: string;
  location?: { lat: number; lon: number } | null;
  created_at: string;
};

export type EventItem = {
  event_id?: string;
  agent_id?: string | null;
  event_type: string;
  payload: unknown;
  created_at: string;
};

export type WsMessage =
  | { type: "subscribed"; payload: { agent_ids: string[] } }
  | { type: "agent.position"; payload: WsAgentPosition }
  | { type: "agent.action"; payload: { agent_id: string; decision: unknown } }
  | { type: "agent.mood_change"; payload: { agent_id: string; old_mood: number; new_mood: number; reason: string; ts: string } }
  | { type: "message.reply"; payload: { agent_id: string; content: string; ts: string } }
  | { type: "sns.new_post"; payload: { post_id: string; agent_id: string; content: string; location?: { lat: number; lon: number } | null; ts: string } }
  | { type: "world.tick"; payload: { started_at: string; completed_at: string; ok: number; errors: number } }
  | { type: "tick.error"; payload: { error: string; message: string } }
  | { type: "error"; payload: { message: string } };
