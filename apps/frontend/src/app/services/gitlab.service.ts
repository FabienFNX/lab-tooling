import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface GitlabUser {
  id: number;
  username: string;
  name: string;
  state: string;
  avatar_url: string;
  web_url: string;
}

export interface GitlabGroup {
  id: number;
  name: string;
  full_path: string;
  description: string | null;
  visibility: string;
  web_url: string;
}

export interface GitlabProject {
  id: number;
  name: string;
  description: string | null;
  visibility: string;
  web_url: string;
  path_with_namespace: string;
}

export interface GitlabMember {
  id: number;
  username: string;
  name: string;
  state: string;
  access_level: number;
  expires_at: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class GitlabService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  getUsers(): Observable<GitlabUser[]> {
    return this.http.get<GitlabUser[]>(`${this.baseUrl}/api/gitlab/users`);
  }

  getGroups(): Observable<GitlabGroup[]> {
    return this.http.get<GitlabGroup[]>(`${this.baseUrl}/api/gitlab/groups`);
  }

  getGroupMembers(groupId: number): Observable<GitlabMember[]> {
    return this.http.get<GitlabMember[]>(`${this.baseUrl}/api/gitlab/groups/${groupId}/members`);
  }

  getProjects(): Observable<GitlabProject[]> {
    return this.http.get<GitlabProject[]>(`${this.baseUrl}/api/gitlab/projects`);
  }

  getProjectMembers(projectId: number): Observable<GitlabMember[]> {
    return this.http.get<GitlabMember[]>(`${this.baseUrl}/api/gitlab/projects/${projectId}/members`);
  }

  addGroupMember(groupId: number, userId: number, accessLevel: number): Observable<GitlabMember> {
    return this.http.post<GitlabMember>(`${this.baseUrl}/api/gitlab/groups/${groupId}/members`, {
      user_id: userId,
      access_level: accessLevel,
    });
  }

  addProjectMember(projectId: number, userId: number, accessLevel: number): Observable<GitlabMember> {
    return this.http.post<GitlabMember>(`${this.baseUrl}/api/gitlab/projects/${projectId}/members`, {
      user_id: userId,
      access_level: accessLevel,
    });
  }
}
