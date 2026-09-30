import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/api/auth';
  private http = inject(HttpClient);

  // Auth state signals
  isLoggedIn = signal<boolean>(!!localStorage.getItem('access_token'));
  currentUser = signal<any>(null);

  constructor() {
    try {
      const cachedUser = localStorage.getItem('user');
      if (cachedUser) {
        this.currentUser.set(JSON.parse(cachedUser));
      }
    } catch {
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      this.isLoggedIn.set(false);
    }
  }

  /**
   * Register — plain POST, does NOT store tokens or auto-login.
   */
  register(data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/register/`, data);
  }

  /**
   * Login — stores tokens + user on success, sets isLoggedIn to true.
   */
  login(data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/login/`, data).pipe(
      tap((res: any) => {
        const access = res.tokens?.access ?? res.access;
        const refresh = res.tokens?.refresh ?? res.refresh;

        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);

        // Build a user object from the JWT payload if the response doesn't include one
        let user = res.user ?? null;
        if (!user && access) {
          try {
            const payload = JSON.parse(atob(access.split('.')[1]));
            user = { id: payload.user_id, username: payload.username ?? `user_${payload.user_id}` };
          } catch {
            user = { id: 0, username: 'lawyer' };
          }
        }
        if (user) {
          localStorage.setItem('user', JSON.stringify(user));
        }

        this.currentUser.set(user);
        this.isLoggedIn.set(true);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    this.currentUser.set(null);
    this.isLoggedIn.set(false);
  }
}
