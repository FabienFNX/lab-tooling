import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Item, ItemCreate } from '../../services/api.service';

@Component({
  selector: 'app-home',
  imports: [FormsModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit {
  private api = inject(ApiService);

  items: Item[] = [];
  newItem: ItemCreate = { name: '', description: '' };
  loading = false;
  error = '';

  ngOnInit(): void {
    this.loadItems();
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
