import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, AdminStats } from '../core/api.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css',
})
export class AdminComponent implements OnInit {
  stats = signal<AdminStats | null>(null);

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getAdminStats().subscribe((s) => this.stats.set(s));
  }
}
