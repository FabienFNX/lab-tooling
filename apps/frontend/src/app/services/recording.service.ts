import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export type RecordingStatus =
  | 'recording'
  | 'stopped'
  | 'transcribing'
  | 'transcribed'
  | 'processing'
  | 'processed'
  | 'error';

export interface Recording {
  id: number;
  session_id: string;
  status: RecordingStatus;
  started_at: string | null;
  stopped_at: string | null;
  duration_seconds: number | null;
  audio_file: string | null;
  transcript_text: string | null;
  processed_text: string | null;
  notion_page_id: string | null;
  notion_url: string | null;
  error_message: string | null;
}

export interface ProcessRequest {
  notion_page_id?: string | null;
}

@Injectable({ providedIn: 'root' })
export class RecordingService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/api/recordings`;

  getRecordings(): Observable<Recording[]> {
    return this.http.get<Recording[]>(this.baseUrl);
  }

  getRecording(id: number): Observable<Recording> {
    return this.http.get<Recording>(`${this.baseUrl}/${id}`);
  }

  startRecording(): Observable<Recording> {
    return this.http.post<Recording>(`${this.baseUrl}/start`, {});
  }

  stopRecording(id: number): Observable<Recording> {
    return this.http.post<Recording>(`${this.baseUrl}/${id}/stop`, {});
  }

  uploadRecording(file: File): Observable<Recording> {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http.post<Recording>(`${this.baseUrl}/upload`, form);
  }

  transcribeRecording(id: number): Observable<Recording> {
    return this.http.post<Recording>(`${this.baseUrl}/${id}/transcribe`, {});
  }

  processRecording(id: number, req: ProcessRequest): Observable<Recording> {
    return this.http.post<Recording>(`${this.baseUrl}/${id}/process`, req);
  }

  deleteRecording(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
