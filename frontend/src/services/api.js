import { getAuthHeaders, getGuestId, auth } from './firebase';

export function getBackendUrl() {
  if (typeof window === 'undefined') return '';
  
  // URL override (?backend=...)
  const params = new URLSearchParams(window.location.search);
  const backendParam = params.get('backend');
  if (backendParam) {
    try {
      const parsed = new URL(backendParam);
      localStorage.setItem('friday_backend_url', parsed.origin);
      return parsed.origin;
    } catch (_) {}
  }

  const stored = localStorage.getItem('friday_backend_url');
  if (stored) return stored;

  // If page is served directly on VPS port 8008 or the VPS IP address
  if (window.location.port === '8008' || window.location.hostname === '213.133.97.141') {
    return window.location.origin;
  }

  const isLocalHost = Boolean(
    window.location.hostname === 'localhost' ||
    window.location.hostname === '[::1]' ||
    window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
  );

  if (isLocalHost) return 'http://127.0.0.1:8008';

  // If running directly on Cloudflare tunnel origin
  if (window.location.origin.includes('trycloudflare.com')) {
    return window.location.origin;
  }

  // If on Vercel preview/production without custom backend override
  if (window.location.hostname.endsWith('.vercel.app')) {
    return 'https://powerpoint-deal-loved-filling.trycloudflare.com';
  }

  // Default: same origin as current page (fastest, 0ms cross-origin overhead)
  return window.location.origin;
}

export const BACKEND_URL = getBackendUrl();

export async function fetchHealth() {
  try {
    const res = await fetch(`${BACKEND_URL}/health`);
    return await res.json();
  } catch (err) {
    console.error('Health check failed', err);
    return null;
  }
}

export async function fetchModels() {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/models`, { headers });
  if (!res.ok) throw new Error(`Failed to fetch models (HTTP ${res.status})`);
  return await res.json();
}

export async function fetchSubscriptionStatus() {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/subscription/status`, { headers });
  if (!res.ok) {
    if (res.status === 401) return null;
    throw new Error(`Failed to fetch subscription status (HTTP ${res.status})`);
  }
  return await res.json();
}

export async function fetchConversations() {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/conversations`, { headers });
  if (!res.ok) {
    if (res.status === 401) return [];
    throw new Error(`Failed to fetch conversations (HTTP ${res.status})`);
  }
  return await res.json();
}

export async function createConversation(id, title = 'New Operation') {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/conversations`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ id, title }),
  });
  if (!res.ok) throw new Error('Failed to create conversation');
  return await res.json();
}

export async function fetchConversationMessages(convId) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/conversations/${convId}`, { headers });
  if (!res.ok) throw new Error('Failed to load conversation history');
  return await res.json();
}

export async function renameConversation(convId, title) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/conversations/${convId}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to rename conversation');
  return await res.json();
}

export async function deleteConversation(convId) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/conversations/${convId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error('Failed to delete conversation');
  return await res.json();
}

export async function createOrder(planId) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/create-order`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ plan_id: planId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Order initiation failed');
  }
  return await res.json();
}

export async function verifyPayment(payload) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/verify-payment`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Payment verification failed');
  return data;
}

/**
 * Robust SSE chat stream reader with anti-blank response safety.
 */
export async function streamChat({
  messages,
  conversationId,
  model,
  onChunk,
  onDone,
  onError,
  signal,
}) {
  const headers = await getAuthHeaders();
  const payload = {
    messages,
    conversation_id: conversationId,
    stream: true,
  };

  const isGuest = !auth.currentUser;
  if (isGuest) {
    payload.guest_id = getGuestId();
  }
  if (model) {
    payload.model = model;
  }

  let response;
  try {
    response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal,
    });
  } catch (err) {
    if (err.name === 'AbortError') return;
    onError(new Error('Network connection error: Failed to reach FRIDAY AI backend.'));
    return;
  }

  if (!response.ok) {
    let errData = {};
    try { errData = await response.json(); } catch (_) {}
    const detail = errData.detail || errData.message || `HTTP ${response.status}`;
    const err = new Error(typeof detail === 'string' ? detail : (detail.message || 'Inference error'));
    err.status = response.status;
    err.detail = detail;
    onError(err);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let receivedAnyTokens = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const eventMatch = part.match(/^event: (\w+)/);
        const dataMatch = part.match(/^data: (.+)$/m);
        if (!dataMatch) continue;

        const eventType = eventMatch ? eventMatch[1] : 'chunk';
        let data;
        try {
          data = JSON.parse(dataMatch[1]);
        } catch (_) {
          continue;
        }

        if (eventType === 'chunk' && data.text) {
          receivedAnyTokens = true;
          onChunk(data.text);
        } else if (eventType === 'done') {
          // If stream finished without any tokens, trigger anti-blank fallback
          if (!receivedAnyTokens) {
            onChunk('FRIDAY Cyber Cloud operational. Threat analysis ready. State your target directive.');
          }
          onDone();
          return;
        } else if (eventType === 'error') {
          onError(new Error(data.message || 'Stream generation interrupted.'));
          return;
        }
      }
    }

    if (!receivedAnyTokens) {
      onChunk('FRIDAY Cyber Cloud standing by. Ready for exploitation instructions.');
    }
    onDone();
  } catch (err) {
    if (err.name === 'AbortError') return;
    onError(err);
  } finally {
    reader.releaseLock();
  }
}

