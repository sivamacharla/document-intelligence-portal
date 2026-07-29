import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  email = 'user@test.com';
  password = 'pass123';
  role = 'user';
  mode = signal<'login' | 'register'>('login');
  error = signal<string | null>(null);
  loading = signal(false);

  constructor(private auth: AuthService, private router: Router) {}

  toggleMode(): void {
    this.mode.set(this.mode() === 'login' ? 'register' : 'login');
    this.error.set(null);
  }

  submit(): void {
    this.error.set(null);
    this.loading.set(true);

    if (this.mode() === 'register') {
      this.auth.register(this.email, this.password, this.role).subscribe({
        next: () => this.doLogin(),
        error: (err) => {
          this.loading.set(false);
          this.error.set(err.error?.detail ?? 'Registration failed');
        },
      });
    } else {
      this.doLogin();
    }
  }

  private doLogin(): void {
    this.auth.login(this.email, this.password).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/chat']);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Login failed');
      },
    });
  }
}
