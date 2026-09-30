import { Component, OnInit, signal, ElementRef, viewChild, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, ConversationItem, ChatMessageItem } from '../../services/chat.service';
import { LegalService } from '../../services/legal.service';

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.css'
})
export class AiChat implements OnInit {
  private chatService = inject(ChatService);
  private legalService = inject(LegalService);
  private cdr = inject(ChangeDetectorRef);
  private scrollArea = viewChild<ElementRef>('scrollArea');

  conversations = signal<ConversationItem[]>([]);
  activeConversation = signal<ConversationItem | null>(null);
  cases = signal<any[]>([]);
  selectedCaseId = signal<number | null>(null);

  messages = signal<ChatMessageItem[]>([]);
  inputQuery = '';
  isGenerating = signal(false);
  currentStreamingText = signal('');
  currentStreamingGrounded = signal<boolean | null>(null);
  errorMessage = signal('');

  private activeAbortController: AbortController | null = null;

  suggestedPrompts = [
    'Summarize key evidence across my active cases',
    'What are the penalties for unauthorized biometric data sharing under Indian law?',
    'Draft a preliminary response strategy for a contract dispute',
    'Explain the procedure for filing a regular bail application under BNSS 2023'
  ];

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.chatService.getConversations().subscribe({
      next: (convs) => {
        this.conversations.set(convs);
        if (convs.length > 0 && !this.activeConversation()) {
          this.selectConversation(convs[0]);
        }
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching conversations:', err)
    });

    this.legalService.getCases().subscribe({
      next: (cList) => {
        this.cases.set(cList);
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching cases:', err)
    });
  }

  createNewConversation(): void {
    const caseId = this.selectedCaseId();
    this.chatService.createConversation('New Legal Consultation', caseId).subscribe({
      next: (conv) => {
        this.conversations.update(list => [conv, ...list]);
        this.selectConversation(conv);
        this.cdr.detectChanges();
      },
      error: (err) => alert('Failed to create chat: ' + (err.error?.error || JSON.stringify(err.error)))
    });
  }

  selectConversation(conv: ConversationItem): void {
    this.activeConversation.set(conv);
    this.messages.set(conv.messages || []);
    if (conv.case_file) {
      this.selectedCaseId.set(conv.case_file);
    }
    this.errorMessage.set('');
    this.scrollToBottom();
    this.cdr.detectChanges();
  }

  onCaseScopeChange(caseId: number | null): void {
    this.selectedCaseId.set(caseId);
    const active = this.activeConversation();
    if (active) {
      this.chatService.updateConversation(active.id, { case_file: caseId }).subscribe({
        next: (updated) => {
          this.activeConversation.set(updated);
          this.conversations.update(list => list.map(c => c.id === updated.id ? updated : c));
          this.cdr.detectChanges();
        },
        error: (err) => alert('Failed to update case focus: ' + (err.error?.error || JSON.stringify(err.error)))
      });
    }
  }

  renameConversation(conv: ConversationItem, event: Event): void {
    event.stopPropagation();
    const newTitle = prompt('Enter new conversation title:', conv.title);
    if (!newTitle || !newTitle.trim()) return;

    this.chatService.updateConversation(conv.id, { title: newTitle.trim() }).subscribe({
      next: (updated) => {
        this.conversations.update(list => list.map(c => c.id === updated.id ? updated : c));
        if (this.activeConversation()?.id === updated.id) {
          this.activeConversation.set(updated);
        }
        this.cdr.detectChanges();
      },
      error: (err) => alert('Failed to rename: ' + JSON.stringify(err.error))
    });
  }

  deleteConversation(conv: ConversationItem, event: Event): void {
    event.stopPropagation();
    if (!confirm(`Delete conversation "${conv.title}"?`)) return;

    this.chatService.deleteConversation(conv.id).subscribe({
      next: () => {
        this.conversations.update(list => list.filter(c => c.id !== conv.id));
        if (this.activeConversation()?.id === conv.id) {
          const remaining = this.conversations();
          if (remaining.length > 0) {
            this.selectConversation(remaining[0]);
          } else {
            this.activeConversation.set(null);
            this.messages.set([]);
          }
        }
        this.cdr.detectChanges();
      },
      error: (err) => alert('Failed to delete chat: ' + JSON.stringify(err.error))
    });
  }

  useSuggestedPrompt(promptText: string): void {
    this.inputQuery = promptText;
    this.sendMessage();
  }

  async sendMessage(): Promise<void> {
    const text = this.inputQuery.trim();
    if (!text || this.isGenerating()) return;

    let conv = this.activeConversation();
    if (!conv) {
      // Auto-create conversation if none selected
      conv = await this.chatService.createConversation('New Legal Consultation', this.selectedCaseId()).toPromise() as ConversationItem;
      if (!conv) return;
      this.conversations.update(list => [conv!, ...list]);
      this.activeConversation.set(conv);
    }

    // Append User message locally
    const userMsg: ChatMessageItem = { role: 'user', content: text, created_at: new Date().toISOString() };
    this.messages.update(msgs => [...msgs, userMsg]);
    this.inputQuery = '';
    this.isGenerating.set(true);
    this.currentStreamingText.set('');
    this.currentStreamingGrounded.set(null);
    this.errorMessage.set('');
    this.scrollToBottom();
    this.cdr.detectChanges();

    this.activeAbortController = new AbortController();

    await this.chatService.sendMessageStream(
      conv.id,
      text,
      (tokenText) => {
        this.currentStreamingText.update(prev => prev + tokenText);
        this.scrollToBottom();
        this.cdr.detectChanges();
      },
      (metadata) => {
        const assistantMsg: ChatMessageItem = {
          role: 'assistant',
          content: metadata.full_text || this.currentStreamingText(),
          grounded: metadata.grounded,
          sources: metadata.sources,
          created_at: new Date().toISOString()
        };
        this.messages.update(msgs => [...msgs, assistantMsg]);
        this.isGenerating.set(false);
        this.currentStreamingText.set('');
        this.activeAbortController = null;
        this.loadData(); // Refresh titles and DB state
        this.scrollToBottom();
        this.cdr.detectChanges();
      },
      (err) => {
        this.isGenerating.set(false);
        this.errorMessage.set(typeof err === 'string' ? err : 'Message generation failed.');
        this.activeAbortController = null;
        this.cdr.detectChanges();
      },
      this.activeAbortController.signal
    );
  }

  stopGeneration(): void {
    if (this.activeAbortController) {
      this.activeAbortController.abort();
      this.activeAbortController = null;
    }
    this.isGenerating.set(false);
    if (this.currentStreamingText().trim()) {
      const partialMsg: ChatMessageItem = {
        role: 'assistant',
        content: this.currentStreamingText() + ' [Stopped]',
        grounded: true,
        created_at: new Date().toISOString()
      };
      this.messages.update(msgs => [...msgs, partialMsg]);
    }
    this.currentStreamingText.set('');
    this.cdr.detectChanges();
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  getSourceLabel(src: any): string {
    if (!src) return '';
    if (typeof src === 'string') return src;
    return src.label || src.file || src.act || JSON.stringify(src);
  }

  formatContentHtml(text: string): string {
    if (!text) return '';
    let formatted = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/### (.*?)\n/g, '<h3 class="font-bold text-slate-900 text-sm mt-3 mb-1">$1</h3>')
      .replace(/ - (.*?)\n/g, '<li class="ml-4 list-disc">$1</li>')
      .replace(/\n\n/g, '<div class="h-2"></div>')
      .replace(/\n/g, '<br/>');
    return formatted;
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const el = this.scrollArea()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    }, 50);
  }
}
