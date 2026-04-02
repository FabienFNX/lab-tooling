import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { GitlabComponent } from './gitlab.component';

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
});
