import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, DocumentItem } from '../core/api.service';

@Component({
  selector: 'app-documents',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './documents.component.html',
  styleUrl: './documents.component.css',
})
export class DocumentsComponent implements OnInit {
  documents = signal<DocumentItem[]>([]);
  uploading = signal(false);
  error = signal<string | null>(null);

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.api.listDocuments().subscribe((docs) => this.documents.set(docs));
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this.uploading.set(true);
    this.error.set(null);
    this.api.uploadDocument(file).subscribe({
      next: () => {
        this.uploading.set(false);
        input.value = '';
        this.refresh();
      },
      error: (err) => {
        this.uploading.set(false);
        this.error.set(err.error?.detail ?? 'Upload failed');
      },
    });
  }

  remove(id: number): void {
    this.api.deleteDocument(id).subscribe(() => this.refresh());
  }
}
