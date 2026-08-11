import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LegalService } from '../../services/legal.service';

@Component({
  selector: 'app-case-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './case-dashboard.html',
  styleUrl: './case-dashboard.css'
})
export class CaseDashboard implements OnInit {
  clients: any[] = [];
  cases: any[] = [];

  // Form states
  newClient = { name: '', email: '', phone: '', address: '' };
  newCase = { title: '', description: '', client: '', status: 'open', citation_tags: '' };

  showClientForm = false;
  showCaseForm = false;

  constructor(private legalService: LegalService) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.legalService.getClients().subscribe({
      next: (data) => this.clients = data,
      error: (err) => console.error('Error fetching clients:', err)
    });

    this.legalService.getCases().subscribe({
      next: (data) => this.cases = data,
      error: (err) => console.error('Error fetching cases:', err)
    });
  }

  addClient(): void {
    if (!this.newClient.name) return;
    this.legalService.createClient(this.newClient).subscribe({
      next: (client) => {
        this.clients.push(client);
        this.newClient = { name: '', email: '', phone: '', address: '' };
        this.showClientForm = false;
      },
      error: (err) => alert('Failed to add client: ' + JSON.stringify(err.error))
    });
  }

  addCase(): void {
    if (!this.newCase.title || !this.newCase.client) return;
    this.legalService.createCase(this.newCase).subscribe({
      next: (c) => {
        this.cases.push(c);
        this.newCase = { title: '', description: '', client: '', status: 'open', citation_tags: '' };
        this.showCaseForm = false;
        this.loadData(); // Reload to resolve names
      },
      error: (err) => alert('Failed to add case: ' + JSON.stringify(err.error))
    });
  }

  getCaseCount(status: string): number {
    return this.cases.filter(c => c.status === status).length;
  }
}
