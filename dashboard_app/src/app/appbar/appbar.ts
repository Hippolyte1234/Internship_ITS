import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { FirebaseAuthService } from '../firebase-auth.service';

@Component({
  selector: 'app-appbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './appbar.html',
  styleUrl: './appbar.css',
})
export class Appbar {
  readonly authService = inject(FirebaseAuthService);
  readonly isOpen = signal(true);

  toggleDrawer(): void {
    this.isOpen.set(!this.isOpen());
  }

  async signOutUser(): Promise<void> {
    await this.authService.signOutUser();
  }
}
