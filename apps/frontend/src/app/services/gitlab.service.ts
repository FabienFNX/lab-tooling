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

export interface EntityResult {
  total: number;
  added: number;
  skipped: number;
  failed: number;
}

export interface AddEverywhereResult {
  groups: EntityResult;
  projects: EntityResult;
}

export interface BulkSelection {
  saved: boolean;
  group_ids: number[];
  project_ids: number[];
}

export interface GitlabUserProfile {
  id: number;
  username: string;
  name: string;
  state: string;
  avatar_url: string;
  web_url: string;
  bio: string | null;
  location: string | null;
  public_email: string | null;
  job_title: string | null;
  organization: string | null;
  created_at: string;
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

  addUserToAllGroupsAndProjects(
    userId: number,
    accessLevel: number,
    groupIds: number[],
    projectIds: number[],
  ): Observable<AddEverywhereResult> {
    return this.http.post<AddEverywhereResult>(
      `${this.baseUrl}/api/gitlab/users/${userId}/add-everywhere`,
      { access_level: accessLevel, group_ids: groupIds, project_ids: projectIds },
    );
  }

  getBulkSelection(): Observable<BulkSelection> {
    return this.http.get<BulkSelection>(`${this.baseUrl}/api/gitlab/bulk-selection`);
  }

  saveBulkSelection(selection: { group_ids: number[]; project_ids: number[] }): Observable<BulkSelection> {
    return this.http.put<BulkSelection>(`${this.baseUrl}/api/gitlab/bulk-selection`, selection);
  }

  getUserProfile(username: string): Observable<GitlabUserProfile> {
    return this.http.get<GitlabUserProfile>(
      `${this.baseUrl}/api/gitlab/users/by-username/${encodeURIComponent(username)}`,
    );
  }
}
