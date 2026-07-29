import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService, ChatSource } from '../core/api.service';
import { AuthService } from '../core/auth.service';
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

  constructor(private api: ApiService, public auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.api.getChatHistory(this.conversationId).subscribe();
  }

  send(): void {
    const text = this.draft.trim();
    if (!text || this.sending()) return;

    this.messages.update((m) => [...m, { role: 'user', content: text }]);
    this.draft = '';
    this.sending.set(true);

    this.api.sendChatMessage(this.conversationId, text).subscribe({
      next: (res) => {
        this.messages.update((m) => [...m, { role: 'assistant', content: res.answer, sources: res.sources }]);
        this.sending.set(false);
      },
      error: () => {
        this.messages.update((m) => [...m, { role: 'assistant', content: 'Something went wrong. Please try again.' }]);
        this.sending.set(false);
      },
    });
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
