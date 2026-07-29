import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { API_BASE_URL } from './environment';

interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
}

const TOKEN_KEY = 'dip_token';
const ROLE_KEY = 'dip_role';

@Injectable({ providedIn: 'root' })
export class AuthService {
  role = signal<string | null>(localStorage.getItem(ROLE_KEY));
  isAuthenticated = signal<boolean>(!!localStorage.getItem(TOKEN_KEY));

  constructor(private http: HttpClient) {}

  register(email: string, password: string, role: string): Observable<unknown> {
    return this.http.post(`${API_BASE_URL}/auth/register`, { email, password, role });
  }

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${API_BASE_URL}/auth/login`, { email, password }).pipe(
      tap((res) => {
        localStorage.setItem(TOKEN_KEY, res.access_token);
        localStorage.setItem(ROLE_KEY, res.role);
        this.role.set(res.role);
        this.isAuthenticated.set(true);
      })
    );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    this.role.set(null);
    this.isAuthenticated.set(false);
  }

  get token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  isAdmin(): boolean {
    return this.role() === 'admin';
  }
}
