import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LegalService } from '../../services/legal.service';

@Component({
  selector: 'app-document-vault',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './document-vault.html',
  styleUrl: './document-vault.css'
})
export class DocumentVault implements OnInit {
  cases: any[] = [];
  documents: any[] = [];

  selectedCaseId: number | null = null;
  selectedFile: File | null = null;
  uploading = false;
  deletingId: number | null = null;

  constructor(private legalService: LegalService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.legalService.getCases().subscribe({
      next: (data) => { this.cases = data; this.cdr.detectChanges(); },
      error: (err) => console.error('Error fetching cases:', err)
    });

    this.legalService.getDocuments().subscribe({
      next: (data) => { this.documents = data; this.cdr.detectChanges(); },
      error: (err) => console.error('Error fetching documents:', err)
    });
  }

  onFileSelected(event: any): void {
    const file: File = event.target.files[0];
    if (file) {
      this.selectedFile = file;
    }
  }

  uploadDocument(): void {
    if (!this.selectedCaseId || !this.selectedFile) {
      alert('Please select a case file and choose a PDF document.');
      return;
    }

    this.uploading = true;
    this.legalService.uploadDocument(this.selectedCaseId, this.selectedFile).subscribe({
      next: (doc) => {
        this.documents.push(doc);
        this.selectedFile = null;
        this.selectedCaseId = null;
        this.uploading = false;
        // Reset file input
        const fileInput = document.getElementById('fileInput') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
        alert('Document uploaded and ingested into ChromaDB successfully!');
        this.loadData();
      },
      error: (err) => {
        this.uploading = false;
        alert('Failed to upload/ingest document: ' + (err.error?.error || JSON.stringify(err.error)));
      }
    });
  }

  deleteDocument(doc: any): void {
    if (!confirm(`Are you sure you want to delete "${doc.name}" from the vault and vector database?`)) {
      return;
    }

    this.deletingId = doc.id;
    this.legalService.deleteDocument(doc.id).subscribe({
      next: () => {
        this.documents = this.documents.filter(d => d.id !== doc.id);
        this.deletingId = null;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.deletingId = null;
        alert('Failed to delete document: ' + (err.error?.detail || err.message || 'Unknown error'));
        this.cdr.detectChanges();
      }
    });
  }
}
