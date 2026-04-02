import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Training {
  id: number;
  trainee_name: string;
  trainee_email: string | null;
  training_title: string;
  training_type: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  score: number | null;
  notes: string | null;
}

export interface TrainingCreate {
  trainee_name: string;
  trainee_email?: string | null;
  training_title: string;
  training_type: string;
  status?: string;
  start_date?: string | null;
  end_date?: string | null;
  score?: number | null;
  notes?: string | null;
}

export interface TrainingStats {
  total: number;
  completed: number;
  in_progress: number;
  planned: number;
  cancelled: number;
  completion_rate: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}

export interface TrainingFilters {
  trainee_name?: string;
  training_type?: string;
  status?: string;
  start_date_from?: string;
  start_date_to?: string;
}

@Injectable({
  providedIn: 'root',
})
export class TrainingService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  getTrainings(filters: TrainingFilters = {}): Observable<Training[]> {
    let params = new HttpParams();
    if (filters.trainee_name) params = params.set('trainee_name', filters.trainee_name);
    if (filters.training_type) params = params.set('training_type', filters.training_type);
    if (filters.status) params = params.set('status', filters.status);
    if (filters.start_date_from) params = params.set('start_date_from', filters.start_date_from);
    if (filters.start_date_to) params = params.set('start_date_to', filters.start_date_to);
    return this.http.get<Training[]>(`${this.baseUrl}/api/trainings`, { params });
  }

  getStats(): Observable<TrainingStats> {
    return this.http.get<TrainingStats>(`${this.baseUrl}/api/trainings/stats`);
  }

  createTraining(payload: TrainingCreate): Observable<Training> {
    return this.http.post<Training>(`${this.baseUrl}/api/trainings`, payload);
  }

  deleteTraining(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/api/trainings/${id}`);
  }

  importExcel(file: File): Observable<Training[]> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<Training[]>(`${this.baseUrl}/api/trainings/import-excel`, form);
  }
}
