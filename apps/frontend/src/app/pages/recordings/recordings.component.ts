import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Recording, RecordingService } from '../../services/recording.service';

@Component({
  selector: 'app-recordings',
  imports: [ReactiveFormsModule, DatePipe],
  templateUrl: './recordings.component.html',
  styleUrl: './recordings.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RecordingsComponent implements OnInit, OnDestroy {
  private svc = inject(RecordingService);
  private router = inject(Router);

  recordings = signal<Recording[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);

  /** The currently active (recording) session, if any */
  activeRecording = computed(() => this.recordings().find((r) => r.status === 'recording') ?? null);
  isRecording = computed(() => this.activeRecording() !== null);

  /** Upload state */
  dragOver = signal(false);
  uploadError = signal<string | null>(null);
  uploading = signal(false);

  /** Poll handle for in-progress recordings */
  private pollHandle: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.loadRecordings();
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  private startPolling(): void {
    this.pollHandle = setInterval(() => {
      const hasActive = this.recordings().some((r) =>
        ['recording', 'transcribing', 'processing'].includes(r.status),
      );
      if (hasActive) {
        this.loadRecordings(false);
      }
    }, 3000);
  }

  private stopPolling(): void {
    if (this.pollHandle !== null) {
      clearInterval(this.pollHandle);
      this.pollHandle = null;
    }
  }

  loadRecordings(showSpinner = true): void {
    if (showSpinner) this.loading.set(true);
    this.svc.getRecordings().subscribe({
      next: (list) => {
        this.recordings.set(list);
        this.loading.set(false);
      },
      error: (e) => {
        this.error.set(e.message ?? 'Failed to load recordings');
        this.loading.set(false);
      },
    });
  }

  startRecording(): void {
    this.error.set(null);
    this.svc.startRecording().subscribe({
      next: (rec) => this.recordings.update((prev) => [rec, ...prev]),
      error: (e) => this.error.set(e.error?.detail ?? e.message ?? 'Failed to start recording'),
    });
  }

  stopRecording(rec: Recording): void {
    this.svc.stopRecording(rec.id).subscribe({
      next: (updated) => this.replaceRecording(updated),
      error: (e) => this.error.set(e.error?.detail ?? e.message ?? 'Failed to stop recording'),
    });
  }

  transcribe(rec: Recording): void {
    this.svc.transcribeRecording(rec.id).subscribe({
      next: (updated) => this.replaceRecording(updated),
      error: (e) => this.error.set(e.error?.detail ?? e.message ?? 'Failed to start transcription'),
    });
  }

  deleteRecording(rec: Recording): void {
    if (!confirm(`Delete recording ${rec.session_id}?`)) return;
    this.svc.deleteRecording(rec.id).subscribe({
      next: () => this.recordings.update((prev) => prev.filter((r) => r.id !== rec.id)),
      error: (e) => this.error.set(e.error?.detail ?? e.message ?? 'Failed to delete recording'),
    });
  }

  openDetail(rec: Recording): void {
    this.router.navigate(['/recordings', rec.id]);
  }

  // ---------------------------------------------------------------------------
  // Upload
  // ---------------------------------------------------------------------------

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) this.doUpload(file);
    input.value = '';
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(true);
  }

  onDragLeave(): void {
    this.dragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) this.doUpload(file);
  }

  private doUpload(file: File): void {
    this.uploading.set(true);
    this.uploadError.set(null);
    this.svc.uploadRecording(file).subscribe({
      next: (rec) => {
        this.recordings.update((prev) => [rec, ...prev]);
        this.uploading.set(false);
      },
      error: (e) => {
        this.uploadError.set(e.error?.detail ?? e.message ?? 'Upload failed');
        this.uploading.set(false);
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private replaceRecording(updated: Recording): void {
    this.recordings.update((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  }

  canTranscribe(rec: Recording): boolean {
    return ['stopped', 'transcribed', 'error'].includes(rec.status) && !!rec.audio_file;
  }

  canProcess(rec: Recording): boolean {
    return ['transcribed', 'processed', 'error'].includes(rec.status) && !!rec.transcript_text;
  }

  formatDuration(seconds: number | null): string {
    if (seconds === null) return '—';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
}
