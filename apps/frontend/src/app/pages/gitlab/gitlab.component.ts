import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  GitlabService,
  GitlabUser,
  GitlabGroup,
  GitlabProject,
  GitlabMember,
} from '../../services/gitlab.service';

type Tab = 'users' | 'groups' | 'projects';

@Component({
  selector: 'app-gitlab',
  imports: [FormsModule],
  templateUrl: './gitlab.component.html',
  styleUrl: './gitlab.component.css',
})
export class GitlabComponent implements OnInit {
  private gitlab = inject(GitlabService);

  activeTab = signal<Tab>('users');

  users = signal<GitlabUser[]>([]);
  groups = signal<GitlabGroup[]>([]);
  projects = signal<GitlabProject[]>([]);

  usersLoading = signal(false);
  groupsLoading = signal(false);
  projectsLoading = signal(false);
  membersLoading = signal(false);

  error = signal('');

  expandedGroupId = signal<number | null>(null);
  expandedProjectId = signal<number | null>(null);

  groupMembers = signal<Record<number, GitlabMember[]>>({});
  projectMembers = signal<Record<number, GitlabMember[]>>({});

  // Add-member form state (shared; only one panel open at a time)
  formUserId: number | null = null;
  formAccessLevel = 30;
  addMemberLoading = signal(false);
  addMemberError = signal('');
  addMemberSuccess = signal('');

  readonly accessLevels = [
    { value: 10, label: 'Guest' },
    { value: 20, label: 'Reporter' },
    { value: 30, label: 'Developer' },
    { value: 40, label: 'Maintainer' },
    { value: 50, label: 'Owner' },
  ];

  ngOnInit(): void {
    this.loadUsers();
    this.loadGroups();
    this.loadProjects();
  }

  setTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  // ── Data loading ────────────────────────────────────────────────────────

  loadUsers(): void {
    this.usersLoading.set(true);
    this.gitlab.getUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.usersLoading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Failed to load users');
        this.usersLoading.set(false);
      },
    });
  }

  loadGroups(): void {
    this.groupsLoading.set(true);
    this.gitlab.getGroups().subscribe({
      next: (groups) => {
        this.groups.set(groups);
        this.groupsLoading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Failed to load groups');
        this.groupsLoading.set(false);
      },
    });
  }

  loadProjects(): void {
    this.projectsLoading.set(true);
    this.gitlab.getProjects().subscribe({
      next: (projects) => {
        this.projects.set(projects);
        this.projectsLoading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Failed to load projects');
        this.projectsLoading.set(false);
      },
    });
  }

  // ── Group expansion ─────────────────────────────────────────────────────

  toggleGroup(groupId: number): void {
    if (this.expandedGroupId() === groupId) {
      this.expandedGroupId.set(null);
    } else {
      this.expandedGroupId.set(groupId);
      this.resetAddMemberForm();
      if (!this.groupMembers()[groupId]) {
        this.loadGroupMembers(groupId);
      }
    }
  }

  loadGroupMembers(groupId: number): void {
    this.membersLoading.set(true);
    this.gitlab.getGroupMembers(groupId).subscribe({
      next: (members) => {
        this.groupMembers.update((m) => ({ ...m, [groupId]: members }));
        this.membersLoading.set(false);
      },
      error: () => {
        this.membersLoading.set(false);
      },
    });
  }

  addGroupMember(groupId: number): void {
    if (!this.formUserId) return;
    this.addMemberLoading.set(true);
    this.addMemberError.set('');
    this.addMemberSuccess.set('');
    this.gitlab.addGroupMember(groupId, this.formUserId, this.formAccessLevel).subscribe({
      next: () => {
        this.addMemberLoading.set(false);
        this.addMemberSuccess.set('Member added successfully');
        this.formUserId = null;
        this.formAccessLevel = 30;
        // Invalidate cache and reload
        this.groupMembers.update((m) => {
          const updated = { ...m };
          delete updated[groupId];
          return updated;
        });
        this.loadGroupMembers(groupId);
      },
      error: (err) => {
        this.addMemberError.set(err?.error?.detail ?? 'Failed to add member');
        this.addMemberLoading.set(false);
      },
    });
  }

  // ── Project expansion ───────────────────────────────────────────────────

  toggleProject(projectId: number): void {
    if (this.expandedProjectId() === projectId) {
      this.expandedProjectId.set(null);
    } else {
      this.expandedProjectId.set(projectId);
      this.resetAddMemberForm();
      if (!this.projectMembers()[projectId]) {
        this.loadProjectMembers(projectId);
      }
    }
  }

  loadProjectMembers(projectId: number): void {
    this.membersLoading.set(true);
    this.gitlab.getProjectMembers(projectId).subscribe({
      next: (members) => {
        this.projectMembers.update((m) => ({ ...m, [projectId]: members }));
        this.membersLoading.set(false);
      },
      error: () => {
        this.membersLoading.set(false);
      },
    });
  }

  addProjectMember(projectId: number): void {
    if (!this.formUserId) return;
    this.addMemberLoading.set(true);
    this.addMemberError.set('');
    this.addMemberSuccess.set('');
    this.gitlab.addProjectMember(projectId, this.formUserId, this.formAccessLevel).subscribe({
      next: () => {
        this.addMemberLoading.set(false);
        this.addMemberSuccess.set('Member added successfully');
        this.formUserId = null;
        this.formAccessLevel = 30;
        // Invalidate cache and reload
        this.projectMembers.update((m) => {
          const updated = { ...m };
          delete updated[projectId];
          return updated;
        });
        this.loadProjectMembers(projectId);
      },
      error: (err) => {
        this.addMemberError.set(err?.error?.detail ?? 'Failed to add member');
        this.addMemberLoading.set(false);
      },
    });
  }

  // ── Helpers ─────────────────────────────────────────────────────────────

  accessLevelLabel(level: number): string {
    return this.accessLevels.find((a) => a.value === level)?.label ?? String(level);
  }

  private resetAddMemberForm(): void {
    this.formUserId = null;
    this.formAccessLevel = 30;
    this.addMemberError.set('');
    this.addMemberSuccess.set('');
  }
}
