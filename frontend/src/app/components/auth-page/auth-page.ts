import { Component, signal, inject } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-auth-page',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './auth-page.html',
  styleUrl: './auth-page.css'
})
export class AuthPageComponent {
  private fb = inject(FormBuilder);
  protected auth = inject(AuthService);

  mode = signal<'register' | 'login'>('register');
  error = signal('');
  info = signal('');
  loading = signal(false);

  registerForm = this.fb.group({
    username: ['', Validators.required],
    email:    ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]]
  });

  loginForm = this.fb.group({
    username: ['', Validators.required],
    password: ['', Validators.required]
  });

  switchMode(target: 'register' | 'login'): void {
    this.mode.set(target);
    this.error.set('');
    this.info.set('');
  }

  onRegister(): void {
    if (this.registerForm.invalid) return;
    this.loading.set(true);
    this.error.set('');
    this.info.set('');

    const data = this.registerForm.getRawValue();
    this.auth.register({ ...data, password2: data.password }).subscribe({
      next: () => {
        this.loading.set(false);
        // Switch to login mode and prefill username
        this.mode.set('login');
        this.loginForm.patchValue({ username: data.username, password: '' });
        this.info.set('Registered successfully. Please sign in.');
        this.registerForm.reset();
      },
      error: (err) => {
        this.loading.set(false);
        const detail = err.error?.detail
          ?? err.error?.username?.[0]
          ?? err.error?.email?.[0]
          ?? JSON.stringify(err.error);
        this.error.set('Registration failed: ' + detail);
      }
    });
  }

  onLogin(): void {
    if (this.loginForm.invalid) return;
    this.loading.set(true);
    this.error.set('');
    this.info.set('');

    this.auth.login(this.loginForm.getRawValue()).subscribe({
      next: () => {
        this.loading.set(false);
        // isLoggedIn is set to true inside auth.login() — root component reacts.
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set('Login failed: ' + (err.error?.detail || 'Invalid credentials'));
      }
    });
  }
}
