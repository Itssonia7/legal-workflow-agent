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
    const cachedUser = localStorage.getItem('user');
    if (cachedUser) {
      this.currentUser.set(JSON.parse(cachedUser));
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
    const accessToken = response.tokens.access;
    const refreshToken = response.tokens.refresh;
    const user = response.user;

    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('user', JSON.stringify(user));

    this.token.set(accessToken);
    this.currentUser.set(user);
  }

  isAuthenticated(): boolean {
    return !!this.token();
  }
}
