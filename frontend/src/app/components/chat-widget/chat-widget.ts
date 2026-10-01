import { Component, signal, ElementRef, viewChild, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';

interface ChatMessage {
  role: 'user' | 'bot';
  text: string;
  grounded?: boolean;
}

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-widget.html',
  styleUrl: './chat-widget.css'
})
export class ChatWidgetComponent {
  private chatService = inject(ChatService);
  private cdr = inject(ChangeDetectorRef);
  private scrollContainer = viewChild<ElementRef>('scrollArea');

  messages = signal<ChatMessage[]>([
    { role: 'bot', text: 'Hi! I can answer public legal questions and explain system features. Sign in or register for full case-aware assistance.' }
  ]);

  inputValue = '';
  isGenerating = signal(false);
  streamingBotText = signal('');
  errorMessage = signal('');

  private activeAbortController: AbortController | null = null;

  async send(): Promise<void> {
    const text = this.inputValue.trim();
    if (!text || this.isGenerating()) return;

    // Append user message
    this.messages.update(msgs => [...msgs, { role: 'user', text }]);
    this.inputValue = '';
    this.isGenerating.set(true);
    this.streamingBotText.set('');
    this.errorMessage.set('');
    this.scrollToBottom();
    this.cdr.detectChanges();

    // Prepare history payload for server
    const history = this.messages().map(m => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.text
    }));

    this.activeAbortController = new AbortController();

    await this.chatService.sendPublicChatMessageStream(
      text,
      history,
      (tokenText) => {
        this.streamingBotText.update(prev => prev + tokenText);
        this.scrollToBottom();
        this.cdr.detectChanges();
      },
      (metadata) => {
        const fullText = metadata.full_text || this.streamingBotText();
        this.messages.update(msgs => [...msgs, {
          role: 'bot',
          text: fullText,
          grounded: metadata.grounded
        }]);
        this.isGenerating.set(false);
        this.streamingBotText.set('');
        this.activeAbortController = null;
        this.scrollToBottom();
        this.cdr.detectChanges();
      },
      (err) => {
        this.isGenerating.set(false);
        this.errorMessage.set(err);
        this.activeAbortController = null;
        this.cdr.detectChanges();
      },
      this.activeAbortController.signal
    );
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      event.preventDefault();
      this.send();
    }
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const el = this.scrollContainer()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }
}
