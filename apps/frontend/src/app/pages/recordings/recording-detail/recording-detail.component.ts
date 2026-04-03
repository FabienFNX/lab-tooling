import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Recording, RecordingService, RecordingStatus } from '../../../services/recording.service';

const IN_PROGRESS_STATUSES: RecordingStatus[] = ['transcribing', 'processing'];

@Component({
  selector: 'app-recording-detail',
  imports: [ReactiveFormsModule],
  templateUrl: './recording-detail.component.html',
  styleUrl: './recording-detail.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RecordingDetailComponent implements OnInit, OnDestroy {
  private svc = inject(RecordingService);
  private router = inject(Router);

  /** Route param passed as input signal */
  id = input.required<string>();

  recording = signal<Recording | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  actionError = signal<string | null>(null);

  isInProgress = computed(() => {
    const rec = this.recording();
    return rec ? IN_PROGRESS_STATUSES.includes(rec.status) : false;
  });

  canTranscribe = computed(() => {
    const rec = this.recording();
    return rec ? ['stopped', 'transcribed', 'error'].includes(rec.status) && !!rec.audio_file : false;
  });

  canProcess = computed(() => {
    const rec = this.recording();
    return rec ? ['transcribed', 'processed', 'error'].includes(rec.status) && !!rec.transcript_text : false;
  });

  processForm = new FormGroup({
    notion_page_id: new FormControl<string>(''),
  });

  private pollHandle: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.loadRecording();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  private loadRecording(silent = false): void {
    if (!silent) this.loading.set(true);
    this.svc.getRecording(+this.id()).subscribe({
      next: (rec) => {
        this.recording.set(rec);
        this.loading.set(false);
        if (IN_PROGRESS_STATUSES.includes(rec.status)) {
          this.ensurePolling();
        } else {
          this.stopPolling();
        }
      },
      error: (e) => {
        this.error.set(e.error?.detail ?? e.message ?? 'Failed to load recording');
        this.loading.set(false);
      },
    });
  }

  private ensurePolling(): void {
    if (this.pollHandle !== null) return;
    this.pollHandle = setInterval(() => this.loadRecording(true), 2000);
  }

  private stopPolling(): void {
    if (this.pollHandle !== null) {
      clearInterval(this.pollHandle);
      this.pollHandle = null;
    }
  }

  transcribe(): void {
    this.actionError.set(null);
    this.svc.transcribeRecording(+this.id()).subscribe({
      next: (rec) => {
        this.recording.set(rec);
        this.ensurePolling();
      },
      error: (e) => this.actionError.set(e.error?.detail ?? e.message ?? 'Transcription failed'),
    });
  }

  process(): void {
    this.actionError.set(null);
    const notion_page_id = this.processForm.value.notion_page_id?.trim() || null;
    this.svc.processRecording(+this.id(), { notion_page_id }).subscribe({
      next: (rec) => {
        this.recording.set(rec);
        this.ensurePolling();
      },
      error: (e) => this.actionError.set(e.error?.detail ?? e.message ?? 'Processing failed'),
    });
  }

  goBack(): void {
    this.router.navigate(['/recordings']);
  }

  formatDuration(seconds: number | null): string {
    if (seconds === null) return '—';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
}
