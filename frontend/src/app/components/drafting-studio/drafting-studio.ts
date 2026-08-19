import { Component, signal, OnInit, ChangeDetectorRef } from '@angular/core';
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

  constructor(
    private legalService: LegalService,
    private cdr: ChangeDetectorRef // Inject the change detector
  ) {}

  ngOnInit(): void {
    this.loadCases();
  }

  loadCases(): void {
    this.legalService.getCases().subscribe({
      next: (data) => {
        this.cases = data;
        if (this.cases.length > 0) {
          this.selectedCaseId = this.cases[0].id;
        }
        this.cdr.detectChanges(); // Force UI update
      },
      error: (err) => console.error('Error fetching cases in drafting studio:', err)
    });
  }

  generateLegalDraft(): void {
    if (!this.draftPrompt.trim() || !this.selectedCaseId) return;
    this.drafting = true;
    this.draftResult = null;
    this.cdr.detectChanges(); // Force loading state to display

    this.legalService.generateDraft(this.draftPrompt, this.selectedCaseId).subscribe({
      next: (res) => {
        this.draftResult = res;
        this.drafting = false;
        this.cdr.detectChanges(); // Force draft result to render
      },
      error: (err) => {
        this.drafting = false;
        this.cdr.detectChanges(); // Force loading state to clear
        alert('Drafting failed: ' + (err.error?.error || JSON.stringify(err.error)));
      }
    });
  }
}
