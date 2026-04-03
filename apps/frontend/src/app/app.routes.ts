import { Route } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';
import { GitlabComponent } from './pages/gitlab/gitlab.component';
import { TrainingComponent } from './pages/training/training.component';

export const appRoutes: Route[] = [
  { path: '', component: HomeComponent, title: 'Home' },
  { path: 'gitlab', component: GitlabComponent, title: 'GitLab' },
  { path: 'training', component: TrainingComponent, title: 'Training' },
  {
    path: 'recordings',
    loadComponent: () =>
      import('./pages/recordings/recordings.component').then((m) => m.RecordingsComponent),
    title: 'Recordings',
  },
  {
    path: 'recordings/:id',
    loadComponent: () =>
      import('./pages/recordings/recording-detail/recording-detail.component').then(
        (m) => m.RecordingDetailComponent,
      ),
    title: 'Recording Detail',
  },
  { path: '**', redirectTo: '' },
];
