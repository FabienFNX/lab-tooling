import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { GitlabComponent } from './gitlab.component';
import { GitlabService } from '../../services/gitlab.service';
import { of, throwError } from 'rxjs';

describe('GitlabComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GitlabComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  it('should create', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    expect(component).toBeTruthy();
  });

  it('should default to the users tab', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    expect(component.activeTab()).toBe('users');
  });

  it('should switch tabs', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    component.setTab('groups');
    expect(component.activeTab()).toBe('groups');
    component.setTab('projects');
    expect(component.activeTab()).toBe('projects');
  });

  it('should return correct access level label', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    expect(component.accessLevelLabel(10)).toBe('Guest');
    expect(component.accessLevelLabel(20)).toBe('Reporter');
    expect(component.accessLevelLabel(30)).toBe('Developer');
    expect(component.accessLevelLabel(40)).toBe('Maintainer');
    expect(component.accessLevelLabel(50)).toBe('Owner');
  });

  it('should expand and collapse a user row', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    expect(component.expandedUserId()).toBeNull();

    component.toggleUser(1);
    expect(component.expandedUserId()).toBe(1);

    component.toggleUser(1);
    expect(component.expandedUserId()).toBeNull();
  });

  it('should switch expanded user when toggling a different user', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    component.toggleUser(1);
    expect(component.expandedUserId()).toBe(1);

    component.toggleUser(2);
    expect(component.expandedUserId()).toBe(2);
  });

  it('should reset add-to-all form when toggling user', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    component.addToAllError.set('some error');
    component.addToAllResult.set({ groups: { total: 1, added: 1, skipped: 0, failed: 0 }, projects: { total: 1, added: 1, skipped: 0, failed: 0 } });

    component.toggleUser(1);
    expect(component.addToAllError()).toBe('');
    expect(component.addToAllResult()).toBeNull();
  });

  it('should call addUserToAllGroupsAndProjects and store result', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    const gitlabService = TestBed.inject(GitlabService);
    const mockResult = {
      groups: { total: 3, added: 2, skipped: 1, failed: 0 },
      projects: { total: 5, added: 4, skipped: 0, failed: 1 },
    };
    jest.spyOn(gitlabService, 'addUserToAllGroupsAndProjects').mockReturnValue(of(mockResult));

    component.bulkAccessLevel = 40;
    component.addUserToAll(42);

    expect(gitlabService.addUserToAllGroupsAndProjects).toHaveBeenCalledWith(42, 40);
    expect(component.addToAllLoading()).toBe(false);
    expect(component.addToAllResult()).toEqual(mockResult);
    expect(component.addToAllError()).toBe('');
  });

  it('should set error on addUserToAll failure', () => {
    const fixture = TestBed.createComponent(GitlabComponent);
    const component = fixture.componentInstance;
    const gitlabService = TestBed.inject(GitlabService);
    jest.spyOn(gitlabService, 'addUserToAllGroupsAndProjects').mockReturnValue(
      throwError(() => ({ error: { detail: 'GITLAB_URL not configured' } }))
    );

    component.addUserToAll(42);

    expect(component.addToAllLoading()).toBe(false);
    expect(component.addToAllError()).toBe('GITLAB_URL not configured');
    expect(component.addToAllResult()).toBeNull();
  });
});
