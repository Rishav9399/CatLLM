const BACKEND_URL = 'http://localhost:8000';

import type { SessionListResponse, SessionDetailResponse } from '@/types';

// ---------------------------------------------------------------------------
// Types — mirroring the exact JSON payload the AgenticOrchestrator emits
// ---------------------------------------------------------------------------
export type SSEEvent =
  | { event: 'status'; content: string }
  | { event: 'token';  content: string }
  | { event: 'error';  content: string }
  | { event: 'done' };

// ---------------------------------------------------------------------------
// createChatSession
// POST /api/v1/chat/sessions  → { session_id: UUID }
// ---------------------------------------------------------------------------
export async function createChatSession(): Promise<string> {
  const res = await fetch(`${BACKEND_URL}/api/v1/chat/sessions`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
  const data = await res.json();
  return data.session_id as string;
}

// ---------------------------------------------------------------------------
// deleteChatSession
// DELETE /api/v1/chat/sessions/{id}
// ---------------------------------------------------------------------------
export async function deleteChatSession(id: string): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/v1/chat/sessions/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete session: ${res.status}`);
}

// ---------------------------------------------------------------------------
// getSessions
// GET /api/v1/chat/sessions?limit=20&offset=0
// ---------------------------------------------------------------------------
export async function getSessions(
  limit = 20,
  offset = 0,
): Promise<SessionListResponse> {
  const res = await fetch(
    `${BACKEND_URL}/api/v1/chat/sessions?limit=${limit}&offset=${offset}`,
  );
  if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// getSession
// GET /api/v1/chat/sessions/{id}
// ---------------------------------------------------------------------------
export async function getSession(id: string): Promise<SessionDetailResponse> {
  const res = await fetch(`${BACKEND_URL}/api/v1/chat/sessions/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// streamMessage
// POST /api/v1/chat/sessions/{id}/message  → text/event-stream (SSE)
// ---------------------------------------------------------------------------
export async function* streamMessage(
  sessionId: string,
  content: string,
  attachments?: string[]
): AsyncGenerator<SSEEvent> {
  const res = await fetch(
    `${BACKEND_URL}/api/v1/chat/sessions/${sessionId}/message`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, attachments }),
    },
  );

  if (!res.ok || !res.body) {
    throw new Error(`Stream request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const messages = buffer.split('\n\n');
    buffer = messages.pop() ?? '';

    for (const message of messages) {
      for (const line of message.split('\n')) {
        if (!line.startsWith('data: ')) continue;
        const dataStr = line.substring(6).trim();
        if (!dataStr) continue;
        try {
          const payload = JSON.parse(dataStr) as SSEEvent;
          yield payload;
        } catch {
          console.error('[SSE] Malformed JSON payload:', dataStr);
        }
      }
    }
  }
}

// ---------------------------------------------------------------------------
// uploadDocument
// POST /api/v1/documents/upload  → { document_id, message, status }
// ---------------------------------------------------------------------------
export async function uploadDocument(
  file: File,
): Promise<{ document_id: string; message: string; status: string }> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${BACKEND_URL}/api/v1/documents/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Upload failed: ${res.status}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// uploadImage
// POST /api/v1/documents/upload_image  → { file_path }
// ---------------------------------------------------------------------------
export async function uploadImage(
  file: File,
): Promise<{ file_path: string }> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${BACKEND_URL}/api/v1/documents/upload_image`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Upload failed: ${res.status}`);
  }

  return res.json();
}
