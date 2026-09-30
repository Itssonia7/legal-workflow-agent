import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface ChatMessageItem {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  grounded?: boolean;
  created_at?: string;
}

export interface ConversationItem {
  id: number;
  user: string;
  title: string;
  case_file?: number | null;
  case_file_title?: string;
  messages: ChatMessageItem[];
  created_at: string;
  updated_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl = 'http://localhost:8000/api/chat';
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private getHeaders(): { headers: HttpHeaders } {
    const token = localStorage.getItem('access_token');
    return {
      headers: new HttpHeaders({
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      })
    };
  }

  // Conversation CRUD
  getConversations(): Observable<ConversationItem[]> {
    return this.http.get<ConversationItem[]>(`${this.apiUrl}/conversations/`, this.getHeaders());
  }

  createConversation(title: string = 'New Legal Consultation', caseFileId?: number | null): Observable<ConversationItem> {
    const payload: any = { title };
    if (caseFileId) payload.case_file = caseFileId;
    return this.http.post<ConversationItem>(`${this.apiUrl}/conversations/`, payload, this.getHeaders());
  }

  updateConversation(id: number, data: Partial<ConversationItem>): Observable<ConversationItem> {
    return this.http.patch<ConversationItem>(`${this.apiUrl}/conversations/${id}/`, data, this.getHeaders());
  }

  deleteConversation(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/conversations/${id}/`, this.getHeaders());
  }

  /**
   * Authenticated SSE Streaming using fetch + ReadableStream.
   * Supports cancellation via AbortController.
   */
  async sendMessageStream(
    conversationId: number,
    query: string,
    onToken: (token: string) => void,
    onComplete: (metadata: { grounded: boolean; full_text: string; sources?: any[] }) => void,
    onError: (err: any) => void,
    abortSignal?: AbortSignal
  ): Promise<void> {
    const token = localStorage.getItem('access_token');
    const url = `${this.apiUrl}/conversations/${conversationId}/send/`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ query }),
        signal: abortSignal
      });

      if (response.status === 401) {
        this.auth.logout();
        onError('Session expired. Please sign in again.');
        return;
      }

      if (!response.ok || !response.body) {
        const errJson = await response.json().catch(() => ({}));
        onError(errJson.error || `HTTP error ${response.status}`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.substring(6);
            try {
              const payload = JSON.parse(dataStr);
              if (payload.error) {
                onError(payload.error);
                return;
              }
              if (payload.token) {
                onToken(payload.token);
              }
              if (payload.done) {
                onComplete({
                  grounded: payload.grounded ?? true,
                  full_text: payload.full_text ?? '',
                  sources: payload.sources ?? []
                });
              }
            } catch (e) {
              // Ignore malformed SSE framing
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('[ChatService] Stream manually stopped by user.');
      } else {
        onError(err.message || 'Streaming failed');
      }
    }
  }

  /**
   * Public Stateless SSE Streaming for the auth-page widget.
   */
  async sendPublicChatMessageStream(
    query: string,
    history: { role: string; content: string }[],
    onToken: (token: string) => void,
    onComplete: (metadata: { grounded: boolean; full_text: string }) => void,
    onError: (err: string) => void,
    abortSignal?: AbortSignal
  ): Promise<void> {
    const url = `${this.apiUrl}/public/`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, history }),
        signal: abortSignal
      });

      if (response.status === 429) {
        onError('Rate limit exceeded. Please wait a minute or sign in for unlimited access.');
        return;
      }

      if (!response.ok || !response.body) {
        const errJson = await response.json().catch(() => ({}));
        onError(errJson.error || 'Public chat error.');
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.substring(6);
            try {
              const payload = JSON.parse(dataStr);
              if (payload.error) {
                onError(payload.error);
                return;
              }
              if (payload.token) {
                onToken(payload.token);
              }
              if (payload.done) {
                onComplete({
                  grounded: payload.grounded ?? true,
                  full_text: payload.full_text ?? ''
                });
              }
            } catch {
              // Ignore framing errors
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        onError(err.message || 'Connection error.');
      }
    }
  }
}
