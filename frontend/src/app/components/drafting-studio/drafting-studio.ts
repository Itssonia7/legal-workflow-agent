import { Component, signal, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LegalService } from '../../services/legal.service';

interface RevisionRecord {
  version: number;
  draft: string;
  feedback?: string;
  timestamp: Date;
}

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
  
  // Document Archetypes (Clean taxonomy without emojis)
  docTypes = [
    { id: 'auto', label: 'Auto-Detect', desc: 'Infers optimal archetype from prompt & context' },
    { id: 'notice', label: 'Legal / Demand Notice', desc: 'Advocate letterhead, statutory violations, 15-day cure demand' },
    { id: 'reply_notice', label: 'Reply to Legal Notice', desc: 'Rebuttal, preliminary objections, para-wise denial' },
    { id: 'bail', label: 'Court Pleading / Bail Application', desc: 'Court caption, cause title, memo of parties, grounds, prayer' },
    { id: 'consumer', label: 'Consumer Complaint', desc: 'District Consumer Commission, deficiency of service, damages' },
    { id: 'affidavit', label: 'Affidavit & Sworn Declaration', desc: 'Deponent identification, sworn statements, verification' },
    { id: 'contract', label: 'Commercial Agreement / Contract', desc: 'Parties, recitals, covenants, termination, execution' }
  ];
  selectedDocType = 'auto';

  // AI Drafting states
  draftPrompt = '';
  draftResult: any = null;
  drafting = false;
  draftStatus: 'idle' | 'drafting' | 'review_pending' | 'accepted' | 'revising' = 'idle';

  // Human-in-the-Loop Revision states
  userFeedback = '';
  showRevisionModal = false;
  revisionHistory: RevisionRecord[] = [];
  isExportingDocx = false;
  copySuccess = false;

  quickSuggestions = [
    'Add an interim bail / urgent hearing prayer clause',
    'Include a strict 15-day statutory notice & cure deadline',
    'Emphasize lack of criminal antecedents & deep roots in society',
    'Make tone more formal and assertive under Indian legal standards',
    'Add statutory citation under Section 439 of BNSS / CrPC',
    'Include clear counsel verification and identification details'
  ];

  constructor(
    private legalService: LegalService,
    private cdr: ChangeDetectorRef
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
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching cases in drafting studio:', err)
    });
  }

  generateLegalDraft(): void {
    if (!this.draftPrompt.trim() || !this.selectedCaseId) return;
    this.drafting = true;
    this.draftStatus = 'drafting';
    this.draftResult = null;
    this.cdr.detectChanges();

    this.legalService.generateDraft(this.draftPrompt, this.selectedCaseId, this.selectedDocType).subscribe({
      next: (res) => {
        this.draftResult = res;
        this.drafting = false;
        this.draftStatus = 'review_pending';
        this.revisionHistory = [
          {
            version: res.revision_count || 1,
            draft: res.current_draft,
            timestamp: new Date()
          }
        ];
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.drafting = false;
        this.draftStatus = 'idle';
        this.cdr.detectChanges();
        alert('Drafting failed: ' + (err.error?.error || JSON.stringify(err.error)));
      }
    });
  }

  acceptDraft(): void {
    this.draftStatus = 'accepted';
    this.cdr.detectChanges();
  }

  openRevisionModal(): void {
    this.showRevisionModal = true;
  }

  closeRevisionModal(): void {
    this.showRevisionModal = false;
  }

  addSuggestion(suggestion: string): void {
    if (this.userFeedback) {
      this.userFeedback += `\n- ${suggestion}`;
    } else {
      this.userFeedback = `- ${suggestion}`;
    }
  }

  submitRevision(): void {
    if (!this.userFeedback.trim() || !this.selectedCaseId || !this.draftResult) return;
    
    this.drafting = true;
    this.draftStatus = 'revising';
    this.showRevisionModal = false;
    this.cdr.detectChanges();

    const previousDraft = this.draftResult.current_draft;
    const currentCount = this.draftResult.revision_count || 1;

    this.legalService.generateDraft(
      this.draftPrompt,
      this.selectedCaseId,
      this.selectedDocType,
      this.userFeedback,
      previousDraft,
      currentCount
    ).subscribe({
      next: (res) => {
        this.draftResult = res;
        this.drafting = false;
        this.draftStatus = 'review_pending';
        this.revisionHistory.unshift({
          version: res.revision_count || currentCount + 1,
          draft: res.current_draft,
          feedback: this.userFeedback,
          timestamp: new Date()
        });
        this.userFeedback = '';
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.drafting = false;
        this.draftStatus = 'review_pending';
        this.cdr.detectChanges();
        alert('Revision failed: ' + (err.error?.error || JSON.stringify(err.error)));
      }
    });
  }

  downloadDocx(): void {
    if (!this.draftResult || !this.draftResult.current_draft) return;
    this.isExportingDocx = true;
    this.cdr.detectChanges();

    const title = `Legal_Draft_Case_${this.selectedCaseId}`;
    const docType = this.draftResult.doc_type || this.selectedDocType || 'bail';

    this.legalService.exportDraftDocx(
      this.draftResult.current_draft,
      title,
      docType,
      this.selectedCaseId
    ).subscribe({
      next: (blob: Blob) => {
        this.isExportingDocx = false;
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `${title}_${docType}.docx`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isExportingDocx = false;
        this.cdr.detectChanges();
        console.error('DOCX Export error:', err);
        // Fallback to text file download if docx export fails
        this.downloadDraftTxt();
      }
    });
  }

  downloadDraftTxt(): void {
    if (!this.draftResult || !this.draftResult.current_draft) return;
    const blob = new Blob([this.draftResult.current_draft], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `legal_draft_case_${this.selectedCaseId}.txt`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  printDocument(): void {
    window.print();
  }

  copyToClipboard(): void {
    if (!this.draftResult || !this.draftResult.current_draft) return;
    navigator.clipboard.writeText(this.draftResult.current_draft).then(() => {
      this.copySuccess = true;
      this.cdr.detectChanges();
      setTimeout(() => {
        this.copySuccess = false;
        this.cdr.detectChanges();
      }, 2500);
    });
  }

  getFormattedDraftHtml(): string {
    if (!this.draftResult || !this.draftResult.current_draft) return '';
    
    const rawLines = this.draftResult.current_draft.split('\n');
    const formattedLines: string[] = [];

    for (let rawLine of rawLines) {
      let line = rawLine.trim();
      if (!line) {
        formattedLines.push('<div class="h-3"></div>');
        continue;
      }

      // 1. Strip conversational opening preambles
      if (/^(here is|here's|below is|certainly|sure|please find|as requested|i will draft|i will generate|i shall draft|i have drafted)/i.test(line)) {
        continue;
      }

      // 2. Strip AI punctuation artifacts: wrapping parentheses '(' ')' or single/double quotes
      line = line.replace(/^\s*\(+['"]?/, '').replace(/['"]?\)+\s*$/, '').trim();
      line = line.replace(/^['"]/, '').replace(/['"]$/, '').trim();

      // Clean line without markdown stars for classifier checks
      let cleanLine = line
        .replace(/^(\d+\.\s*)?\*{0,2}(COURT JURISDICTION|DOCUMENT TITLE|CAUSE TITLE|MEMO OF PARTIES)\*{0,2}\s*[:\-]\s*/i, '')
        .replace(/\*\*:/g, ':')
        .replace(/:\*\*/g, ':')
        .replace(/^[#*]+\s*/, '')
        .replace(/[*#]+$/, '');

      // Apply bold formatting inside line for remaining markdown
      let htmlLine = cleanLine.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-slate-900">$1</strong>');

      // Check section headers (which get the clean uppercase divider styling)
      const isLetterheadHeader = /^(\d+\.\s*)?\*{0,2}ADVOCATE('?S)?\s+LETTERHEAD/i.test(line);
      const isSectionHeader = /^(\d+\.\s*)?\*{0,2}(ADVOCATE LETTERHEAD|MODE OF TRANSMISSION|NOTICEE PARTICULARS|SUBJECT LINE|AUTHORIZATION STATEMENT|STATEMENT OF FACTS|FACTS OF THE CASE|FACTS|LEGAL GROUNDS|STATUTORY CITATIONS|LEGAL BASIS|DEMAND|DEMANDS|CONSEQUENCE|CONSEQUENCES|GROUNDS|PRAYER|VERIFICATION|RECITALS|OPERATIVE|DEPONENT|SCHEDULE|ANNEXURE|PRELIMINARY OBJECTIONS|PARA-WISE REPLY|ADVOCATE SIGNATURE|NOTICEE COPY|RECORD COPY|COMMISSION JURISDICTION|COMPLAINT NO|DEFICIENCY OF SERVICE|UNFAIR TRADE PRACTICE|ATTESTATION BLOCK|DATE AND PARTIES|EXECUTION & WITNESS)\*{0,2}[:\-]?/i.test(line) ||
        (/^(\*\*.*?\*\*)$/.test(line) && line.length < 90 && !/^(Sub|Subject)/i.test(cleanLine));

      const isSubjectBox = /^(\*\*.*?\*\*)$/.test(line) && /LEGAL NOTICE/i.test(line) && !/^\d+\./.test(line);
      const isSubjectLine = /^(Sub|Subject)\s*[:\-]/i.test(cleanLine);
      const isCourtHeader = /^(IN THE COURT OF|IN THE HIGH COURT|BEFORE THE HON'BLE|IN THE SUPREME COURT|BEFORE THE DISTRICT)/i.test(cleanLine);
      const isMainTitle = /^(BAIL APPLICATION|LEGAL NOTICE|REPLY TO LEGAL NOTICE|AFFIDAVIT|NON-DISCLOSURE AGREEMENT|PETITION UNDER|APPLICATION UNDER|COMMERCIAL LEASE|CONSUMER COMPLAINT)/i.test(cleanLine) && !isSectionHeader;
      const isMemoParties = /^(MEMO OF PARTIES|.*?\.\.\.\s*(APPLICANT|PETITIONER|PLAINTIFF|COMPLAINANT)\s+VERSUS\s+.*?\.\.\.\s*(RESPONDENT|DEFENDANT|OPPOSITE PARTY))/i.test(cleanLine);
      const isSignature = /^(THROUGH:|COUNSEL FOR|DEPONENT|ADVOCATE|IN WITNESS WHEREOF|VERIFICATION:|YOURS FAITHFULLY|\[ADVOCATE|ADV\.\s|Advocate for)/i.test(cleanLine);

      if (isLetterheadHeader || isSectionHeader) {
        formattedLines.push(`<div class="font-serif font-bold text-xs md:text-sm uppercase tracking-wider text-slate-900 mt-5 mb-2 border-b border-gray-200 pb-1">${htmlLine}</div>`);
      } else if (isSubjectBox || isSubjectLine) {
        formattedLines.push(`<div class="font-serif font-bold text-xs md:text-sm text-slate-900 my-2 bg-slate-50 p-2.5 border-l-2 border-slate-900 leading-snug">${htmlLine}</div>`);
      } else if (isCourtHeader) {
        formattedLines.push(`<div class="text-center font-serif font-bold text-sm md:text-base tracking-wider uppercase text-slate-900 my-2">${htmlLine}</div>`);
      } else if (isMainTitle) {
        formattedLines.push(`<div class="text-center font-serif font-bold text-xs md:text-sm tracking-wide uppercase text-slate-900 my-2 border-y border-gray-300 py-1.5">${htmlLine}</div>`);
      } else if (isMemoParties) {
        formattedLines.push(`<div class="text-center font-serif font-semibold text-xs md:text-sm tracking-normal text-slate-800 my-3 bg-slate-50 p-2.5 border border-slate-200 rounded">${htmlLine}</div>`);
      } else if (isSignature) {
        formattedLines.push(`<div class="text-right font-serif font-bold text-xs md:text-sm text-slate-900 mt-6 mb-1 space-y-1">${htmlLine}</div>`);
      } else if (/^(\d+\.|\([a-z]\)|[A-Z]\.)\s+/.test(htmlLine)) {
        formattedLines.push(`<p class="font-serif text-xs md:text-sm leading-relaxed text-slate-800 text-justify mb-2.5 pl-4 -indent-4">${htmlLine}</p>`);
      } else {
        formattedLines.push(`<p class="font-serif text-xs md:text-sm leading-relaxed text-slate-800 text-justify mb-2.5">${htmlLine}</p>`);
      }
    }

    return formattedLines.join('\n');
  }

  getDocTypeBadge(typeId?: string): string {
    const found = this.docTypes.find(d => d.id === (typeId || this.draftResult?.doc_type || this.selectedDocType));
    return found ? found.label : 'Legal Instrument';
  }
}
