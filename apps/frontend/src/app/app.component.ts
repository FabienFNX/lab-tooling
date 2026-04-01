import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Item, ItemCreate } from './services/api.service';

@Component({
  imports: [FormsModule],
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit {
  private api = inject(ApiService);

  title = 'Lab Tooling';
  healthStatus = '';
  items: Item[] = [];
  newItem: ItemCreate = { name: '', description: '' };
  loading = false;
  error = '';

  ngOnInit(): void {
    this.checkHealth();
    this.loadItems();
  }

  checkHealth(): void {
    this.api.getHealth().subscribe({
      next: (res) => (this.healthStatus = res.status),
      error: () => (this.healthStatus = 'unavailable'),
    });
  }

  loadItems(): void {
    this.loading = true;
    this.api.getItems().subscribe({
      next: (items) => {
        this.items = items;
        this.loading = false;
      },
      error: () => {
        this.error = 'Failed to load items';
        this.loading = false;
      },
    });
  }

  createItem(): void {
    if (!this.newItem.name.trim()) return;
    this.api.createItem(this.newItem).subscribe({
      next: (item) => {
        this.items = [...this.items, item];
        this.newItem = { name: '', description: '' };
      },
      error: () => (this.error = 'Failed to create item'),
    });
  }
}
