import { Route } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';
import { GitlabComponent } from './pages/gitlab/gitlab.component';

export const appRoutes: Route[] = [
  { path: '', component: HomeComponent, title: 'Home' },
  { path: 'gitlab', component: GitlabComponent, title: 'GitLab' },
  { path: '**', redirectTo: '' },
];
