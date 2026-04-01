import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Item {
  id: number;
  name: string;
  description?: string;
}

export interface ItemCreate {
  name: string;
  description?: string;
}

export interface HealthStatus {
  status: string;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getHealth(): Observable<HealthStatus> {
    return this.http.get<HealthStatus>(`${this.baseUrl}/health`);
  }

  getItems(): Observable<Item[]> {
    return this.http.get<Item[]>(`${this.baseUrl}/api/items`);
  }

  createItem(item: ItemCreate): Observable<Item> {
    return this.http.post<Item>(`${this.baseUrl}/api/items`, item);
  }
}
