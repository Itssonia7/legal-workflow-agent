import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/api/auth';
  
  // Signals to hold authentication state
  currentUser = signal<any>(null);
  token = signal<string | null>(localStorage.getItem('access_token'));

  constructor(private http: HttpClient) {
    try {
      const cachedUser = localStorage.getItem('user');
      if (cachedUser) {
        this.currentUser.set(JSON.parse(cachedUser));
      }
    } catch {
      // Corrupted localStorage — clear it
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }

  register(data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/register/`, data).pipe(
      tap((res: any) => this.handleAuthSuccess(res))
    );
  }

  login(data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/login/`, data).pipe(
      tap((res: any) => this.handleAuthSuccess(res))
    );
  }
  
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    this.currentUser.set(null);
    this.token.set(null);
  }

  private handleAuthSuccess(response: any): void {
    // Login (TokenObtainPairView) returns flat: { access, refresh }
    // Register (custom RegisterView) returns nested: { tokens: { access, refresh }, user: {...} }
    const accessToken = response.tokens?.access ?? response.access;
    const refreshToken = response.tokens?.refresh ?? response.refresh;
    let user = response.user ?? null;

    // TokenObtainPairView doesn't return a user object — decode the JWT to
    // build a minimal one so that currentUser signal becomes truthy and the
    // UI transitions from the login form to the dashboard.
    if (!user && accessToken) {
      try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        user = { id: payload.user_id, username: payload.username ?? `user_${payload.user_id}` };
      } catch {
        user = { id: 0, username: 'lawyer' };
      }
    }

    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    }

    this.token.set(accessToken);
    this.currentUser.set(user);
  }

  isAuthenticated(): boolean {
    return !!this.token();
  }
}
