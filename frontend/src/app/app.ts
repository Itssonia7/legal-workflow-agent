import { Component, signal } from '@angular/core';
import { CaseDashboard } from './components/case-dashboard/case-dashboard';
import { DocumentVault } from './components/document-vault/document-vault';
import { Calendar } from './components/calendar/calendar';
import { DraftingStudio } from './components/drafting-studio/drafting-studio';
import { AuthPageComponent } from './components/auth-page/auth-page';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CaseDashboard, DocumentVault, Calendar, DraftingStudio, AuthPageComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  title = 'Autonomous Legal Workflow Console';

  // Tab state
  activeTab = signal<'dashboard' | 'vault' | 'calendar' | 'drafting'>('dashboard');

  constructor(public authService: AuthService) {}

  logout(): void {
    this.authService.logout();
    this.activeTab.set('dashboard');
  }
}
