import { Component, signal, ElementRef, viewChild } from '@angular/core';

interface ChatMessage {
  role: 'user' | 'bot';
  text: string;
}

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [],
  templateUrl: './chat-widget.html',
  styleUrl: './chat-widget.css'
})
export class ChatWidgetComponent {
  private scrollContainer = viewChild<ElementRef>('scrollArea');

  messages = signal<ChatMessage[]>([
    { role: 'bot', text: 'Hi! I can help you understand how this system works. Sign in or register to get started.' }
  ]);

  inputValue = '';

  send(): void {
    const text = this.inputValue.trim();
    if (!text) return;

    // Append user message
    this.messages.update(msgs => [...msgs, { role: 'user', text }]);
    this.inputValue = '';

    // TODO: replace with real API call later
    setTimeout(() => {
      this.messages.update(msgs => [...msgs, { role: 'bot', text: 'Chatbot is coming soon.' }]);
      this.scrollToBottom();
    }, 300);

    this.scrollToBottom();
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
