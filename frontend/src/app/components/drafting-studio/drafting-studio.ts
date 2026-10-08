import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LegalService } from '../../services/legal.service';

@Component({
  selector: 'app-drafting-studio',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './drafting-studio.html',
  styleUrl: './drafting-studio.css'
})
export class DraftingStudio implements OnInit {
  cases: any[] = [];
  selectedCaseId: number | null = null;

  // AI Drafting states
  draftPrompt = '';
  draftResult: any = null;
  drafting = false;

  // Draft History states
  draftHistory: any[] = [];
  historyLoading = false;
  historyError = false;
  expandedDraftId: number | null = null;

  constructor(
    private legalService: LegalService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadCases();
    this.loadDraftHistory();
  }

  loadCases(): void {
    this.legalService.getCases().subscribe({
      next: (data) => {
        this.cases = data;
        if (this.cases.length > 0) {
          this.selectedCaseId = this.cases[0].id;
        }
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching cases in drafting studio:', err)
    });
  }

  loadDraftHistory(): void {
    this.historyLoading = true;
    this.historyError = false;
    this.legalService.getDraftHistory().subscribe({
      next: (data) => {
        this.draftHistory = data;
        this.historyLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching draft history:', err);
        this.historyLoading = false;
        this.historyError = true;
        this.cdr.detectChanges();
      }
    });
  }

  generateLegalDraft(): void {
    if (!this.draftPrompt.trim() || !this.selectedCaseId) return;
    this.drafting = true;
    this.draftResult = null;
    this.cdr.detectChanges();

    this.legalService.generateDraft(this.draftPrompt, this.selectedCaseId).subscribe({
      next: (res) => {
        this.draftResult = res;
        this.drafting = false;
        this.cdr.detectChanges();
        // Refresh history so the new record appears immediately
        this.loadDraftHistory();
      },
      error: (err) => {
        this.drafting = false;
        this.cdr.detectChanges();
        alert('Drafting failed: ' + (err.error?.error || JSON.stringify(err.error)));
      }
    });
  }

  toggleExpandDraft(id: number): void {
    this.expandedDraftId = this.expandedDraftId === id ? null : id;
  }

  reusePrompt(item: any): void {
    this.draftPrompt = item.prompt;
    if (item.case_file) {
      this.selectedCaseId = item.case_file;
    }
    // Scroll to top so user sees the pre-filled form
    window.scrollTo({ top: 0, behavior: 'smooth' });
    this.cdr.detectChanges();
  }
}
