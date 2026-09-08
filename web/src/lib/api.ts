export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "https://assessiq1.onrender.com";

export type Role = "user" | "assistant";

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface Recommendation {
  name: string;
  url: string;
  test_type: "K" | "A" | "P" | "C" | "B" | "D" | "E" | "S" | string;
  score: number;
  reason: string;
}

export interface ChatResponse {
  reply: string;
  recommendations: Recommendation[];
  end_of_conversation: boolean;
  /** Per-stage latency in ms: guardrails / retrieval / generation / validation / total */
  timings?: Record<string, number>;
}

export const TEST_TYPE_LABELS: Record<string, string> = {
  A: "Ability & Aptitude",
  B: "Biodata & Situational",
  C: "Competency Based",
  D: "Development & 360",
  E: "Assessment Exercises",
  K: "Knowledge & Skills",
  P: "Personality & Behavior",
  S: "Simulations",
};

export class BackendUnreachableError extends Error {}

export async function sendChat(
  messages: ChatMessage[],
  signal?: AbortSignal,
): Promise<ChatResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
      signal,
    });
  } catch {
    throw new BackendUnreachableError(
      "Couldn't reach the assessment engine.",
    );
  }

  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }

  return res.json();
}
