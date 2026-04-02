import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  Training,
  TrainingCreate,
  TrainingFilters,
  TrainingService,
  TrainingStats,
} from '../../services/training.service';

type Tab = 'records' | 'import' | 'dashboard';

const TRAINING_TYPES = ['onboarding', 'security', 'technical', 'soft-skills', 'compliance', 'other'];
const STATUSES = ['planned', 'in-progress', 'completed', 'cancelled'];

@Component({
  selector: 'app-training',
  imports: [FormsModule],
  templateUrl: './training.component.html',
  styleUrl: './training.component.css',
})
export class TrainingComponent implements OnInit {
  private svc = inject(TrainingService);

  // ── Tabs ──────────────────────────────────────────────────────────────────
  activeTab = signal<Tab>('records');

  // ── Records tab ───────────────────────────────────────────────────────────
  trainings = signal<Training[]>([]);
  recordsLoading = signal(false);
  recordsError = signal('');

  filters: TrainingFilters = {};
  filterName = '';
  filterType = '';
  filterStatus = '';
  filterDateFrom = '';
  filterDateTo = '';

  // ── Create form ───────────────────────────────────────────────────────────
  showCreateForm = signal(false);
  createLoading = signal(false);
  createError = signal('');
  createSuccess = signal('');
  newRecord: TrainingCreate = {
    trainee_name: '',
    trainee_email: '',
    training_title: '',
    training_type: 'technical',
    status: 'planned',
    start_date: '',
    end_date: '',
    score: null,
    notes: '',
  };

  // ── Import tab ────────────────────────────────────────────────────────────
  importFile: File | null = null;
  importFileName = signal('');
  importLoading = signal(false);
  importError = signal('');
  importResult = signal<Training[] | null>(null);

  // ── Dashboard tab ─────────────────────────────────────────────────────────
  stats = signal<TrainingStats | null>(null);
  statsLoading = signal(false);
  statsError = signal('');

  readonly trainingTypes = TRAINING_TYPES;
  readonly statuses = STATUSES;

  // ── Computed helpers ──────────────────────────────────────────────────────
  typeBarData = computed(() => {
    const s = this.stats();
    if (!s || !s.total) return [];
    return Object.entries(s.by_type)
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => ({ type, count, pct: Math.round((count / s.total) * 100) }));
  });

  statusBarData = computed(() => {
    const s = this.stats();
    if (!s || !s.total) return [];
    const colors: Record<string, string> = {
      completed: '#28a745',
      'in-progress': '#007bff',
      planned: '#6c757d',
      cancelled: '#dc3545',
    };
    return Object.entries(s.by_status)
      .sort((a, b) => b[1] - a[1])
      .map(([status, count]) => ({
        status,
        count,
        pct: Math.round((count / s.total) * 100),
        color: colors[status] ?? '#999',
      }));
  });

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  ngOnInit(): void {
    this.loadRecords();
    this.loadStats();
  }

  // ── Tab helpers ────────────────────────────────────────────────────────────
  setTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  // ── Records ────────────────────────────────────────────────────────────────
  loadRecords(): void {
    this.recordsLoading.set(true);
    this.recordsError.set('');
    const filters: TrainingFilters = {};
    if (this.filterName.trim()) filters.trainee_name = this.filterName.trim();
    if (this.filterType) filters.training_type = this.filterType;
    if (this.filterStatus) filters.status = this.filterStatus;
    if (this.filterDateFrom) filters.start_date_from = this.filterDateFrom;
    if (this.filterDateTo) filters.start_date_to = this.filterDateTo;
    this.svc.getTrainings(filters).subscribe({
      next: (data) => {
        this.trainings.set(data);
        this.recordsLoading.set(false);
      },
      error: (err) => {
        this.recordsError.set(err?.error?.detail ?? 'Failed to load training records');
        this.recordsLoading.set(false);
      },
    });
  }

  applyFilters(): void {
    this.loadRecords();
  }

  clearFilters(): void {
    this.filterName = '';
    this.filterType = '';
    this.filterStatus = '';
    this.filterDateFrom = '';
    this.filterDateTo = '';
    this.loadRecords();
  }

  deleteRecord(id: number): void {
    if (!confirm('Delete this training record?')) return;
    this.svc.deleteTraining(id).subscribe({
      next: () => {
        this.trainings.update((list) => list.filter((t) => t.id !== id));
        this.loadStats();
      },
      error: (err) => {
        this.recordsError.set(err?.error?.detail ?? 'Failed to delete record');
      },
    });
  }

  // ── Create ─────────────────────────────────────────────────────────────────
  toggleCreateForm(): void {
    this.showCreateForm.update((v) => !v);
    this.createError.set('');
    this.createSuccess.set('');
  }

  submitCreate(): void {
    if (!this.newRecord.trainee_name.trim() || !this.newRecord.training_title.trim() || !this.newRecord.training_type) {
      this.createError.set('Trainee name, title and type are required.');
      return;
    }
    this.createLoading.set(true);
    this.createError.set('');
    this.createSuccess.set('');
    const payload: TrainingCreate = {
      ...this.newRecord,
      trainee_email: this.newRecord.trainee_email || null,
      start_date: this.newRecord.start_date || null,
      end_date: this.newRecord.end_date || null,
      notes: this.newRecord.notes || null,
    };
    this.svc.createTraining(payload).subscribe({
      next: (created) => {
        this.trainings.update((list) => [created, ...list]);
        this.createLoading.set(false);
        this.createSuccess.set('Training record created.');
        this.newRecord = {
          trainee_name: '',
          trainee_email: '',
          training_title: '',
          training_type: 'technical',
          status: 'planned',
          start_date: '',
          end_date: '',
          score: null,
          notes: '',
        };
        this.loadStats();
      },
      error: (err) => {
        this.createError.set(err?.error?.detail ?? 'Failed to create record');
        this.createLoading.set(false);
      },
    });
  }

  // ── Import ─────────────────────────────────────────────────────────────────
  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.importFile = file;
    this.importFileName.set(file?.name ?? '');
    this.importError.set('');
    this.importResult.set(null);
  }

  submitImport(): void {
    if (!this.importFile) return;
    this.importLoading.set(true);
    this.importError.set('');
    this.importResult.set(null);
    this.svc.importExcel(this.importFile).subscribe({
      next: (records) => {
        this.importResult.set(records);
        this.importLoading.set(false);
        this.loadRecords();
        this.loadStats();
      },
      error: (err) => {
        this.importError.set(err?.error?.detail ?? 'Import failed');
        this.importLoading.set(false);
      },
    });
  }

  // ── Dashboard ──────────────────────────────────────────────────────────────
  loadStats(): void {
    this.statsLoading.set(true);
    this.statsError.set('');
    this.svc.getStats().subscribe({
      next: (s) => {
        this.stats.set(s);
        this.statsLoading.set(false);
      },
      error: (err) => {
        this.statsError.set(err?.error?.detail ?? 'Failed to load statistics');
        this.statsLoading.set(false);
      },
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  statusClass(status: string): string {
    const map: Record<string, string> = {
      completed: 'status-completed',
      'in-progress': 'status-in-progress',
      planned: 'status-planned',
      cancelled: 'status-cancelled',
    };
    return map[status] ?? 'status-planned';
  }
}
