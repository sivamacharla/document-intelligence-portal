import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from './environment';

export interface DocumentItem {
  id: number;
  filename: string;
  content_type: string;
  chunk_count: number;
  created_at: string;
}

export interface ChatSource {
  document_id: number;
  filename: string;
  chunk_preview: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}

export interface ChatHistoryItem {
  role: string;
  content: string;
  created_at: string;
}

export interface AdminStats {
  total_users: number;
  total_documents: number;
  total_chat_messages: number;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  listDocuments(): Observable<DocumentItem[]> {
    return this.http.get<DocumentItem[]>(`${API_BASE_URL}/documents`);
  }

  uploadDocument(file: File): Observable<DocumentItem> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<DocumentItem>(`${API_BASE_URL}/documents/upload`, form);
  }

  deleteDocument(id: number): Observable<unknown> {
    return this.http.delete(`${API_BASE_URL}/documents/${id}`);
  }

  sendChatMessage(conversationId: string, message: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${API_BASE_URL}/chat/query`, { conversation_id: conversationId, message });
  }

  getChatHistory(conversationId: string): Observable<ChatHistoryItem[]> {
    return this.http.get<ChatHistoryItem[]>(`${API_BASE_URL}/chat/history/${conversationId}`);
  }

  getAdminStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(`${API_BASE_URL}/admin/stats`);
  }
}
