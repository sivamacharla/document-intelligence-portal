import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';
import { ApiService, ChatSource } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { API_BASE_URL } from '../core/environment';
import { DocumentsComponent } from '../documents/documents.component';

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, DocumentsComponent, RouterLink],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',
})
export class ChatComponent implements OnInit {
  conversationId = crypto.randomUUID().slice(0, 8);
  messages = signal<DisplayMessage[]>([]);
  draft = '';
  sending = signal(false);

  constructor(private api: ApiService, public auth: AuthService, private router: Router, private sanitizer: DomSanitizer) {}

  ngOnInit(): void {
    this.api.getChatHistory(this.conversationId).subscribe();
  }

  renderContent(msg: DisplayMessage): SafeHtml {
    const escaped = msg.content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    const sources = msg.sources ?? [];
    const withCitations = escaped.replace(/\[(\d+)\]/g, (match, numStr) => {
      const source = sources[Number(numStr) - 1];
      if (!source) return match;
      const title = source.filename.replace(/"/g, '&quot;');
      return `<sup class="cite" title="${title}">${numStr}</sup>`;
    });

    return this.sanitizer.bypassSecurityTrustHtml(withCitations);
  }

  async send(): Promise<void> {
    const text = this.draft.trim();
    if (!text || this.sending()) return;

    this.messages.update((m) => [...m, { role: 'user', content: text }]);
    this.draft = '';
    this.sending.set(true);

    const assistantMsg: DisplayMessage = { role: 'assistant', content: '' };
    this.messages.update((m) => [...m, assistantMsg]);

    try {
      const res = await fetch(`${API_BASE_URL}/chat/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.auth.token}`,
        },
        body: JSON.stringify({ conversation_id: this.conversationId, message: text }),
      });

      if (!res.ok || !res.body) throw new Error(`request failed: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';

        for (const event of events) {
          if (!event.startsWith('data: ')) continue;
          const payload = JSON.parse(event.slice(6));
          if (payload.delta) {
            assistantMsg.content += payload.delta;
          } else if (payload.done) {
            assistantMsg.sources = payload.sources;
          }
          this.messages.update((m) => [...m]);
        }
      }
    } catch {
      assistantMsg.content = 'Something went wrong. Please try again.';
      this.messages.update((m) => [...m]);
    } finally {
      this.sending.set(false);
    }
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
