import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CaseDashboard } from './components/case-dashboard/case-dashboard';
import { DocumentVault } from './components/document-vault/document-vault';
import { Calendar } from './components/calendar/calendar';
import { DraftingStudio } from './components/drafting-studio/drafting-studio';
import { AuthService } from './services/auth.service';
import { LegalService } from './services/legal.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, CaseDashboard, DocumentVault, Calendar, DraftingStudio],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  title = 'Autonomous Legal Workflow Console';
  
  // Tab states
  activeTab = signal<'dashboard' | 'vault' | 'calendar' | 'drafting'>('dashboard');
  
  // Auth states
  isLoginMode = signal<boolean>(true);
  authData = { username: '', password: '', email: '', phone: '' };

  constructor(
    public authService: AuthService,
    private legalService: LegalService
  ) {}

  ngOnInit(): void {
    // Check if user is already authenticated
    this.authService.isAuthenticated();
  }

  toggleAuthMode(): void {
    this.isLoginMode.update(val => !val);
  }

  handleAuth(): void {
    if (this.isLoginMode()) {
      // Login
      this.authService.login({
        username: this.authData.username,
        password: this.authData.password
      }).subscribe({
        next: () => {
          this.authData = { username: '', password: '', email: '', phone: '' };
        },
        error: (err) => alert('Login failed: ' + (err.error?.detail || 'Invalid credentials'))
      });
    } else {
      // Register
      this.authService.register({
        username: this.authData.username,
        email: this.authData.email,
        password: this.authData.password,
        password2: this.authData.password, // Simple reuse for confirm
        phone: this.authData.phone
      }).subscribe({
        next: () => {
          this.authData = { username: '', password: '', email: '', phone: '' };
          this.isLoginMode.set(true);
          alert('Registration successful! Please login.');
        },
        error: (err) => alert('Registration failed: ' + JSON.stringify(err.error))
      });
    }
  }

  logout(): void {
    this.authService.logout();
    this.activeTab.set('dashboard');
  }
}
