import { Component, OnInit, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ApiService } from './services/api.service';

@Component({
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit {
  private api = inject(ApiService);

  title = 'Lab Tooling';
  healthStatus = '';

  ngOnInit(): void {
    this.checkHealth();
  }

  checkHealth(): void {
    this.api.getHealth().subscribe({
      next: (res) => (this.healthStatus = res.status),
      error: () => (this.healthStatus = 'unavailable'),
    });
  }
}
