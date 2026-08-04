import { ChangeDetectionStrategy, Component, computed, inject, signal, effect } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FirebaseAuthService } from '../app/firebase-auth.service';
import { AiChartComponent } from '../graphics/graphics_controller';
import { AsyncPipe } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [ReactiveFormsModule, AiChartComponent],
  templateUrl: './dashboard.html',
  styles: [':host { display: block; padding: 2rem; }'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardPage {
  private readonly authService = inject(FirebaseAuthService);

  readonly userEmail = computed(() => this.authService.currentUser()?.email ?? 'guest@example.com');
  readonly currentUser = computed(() => this.authService.currentUser());

  // 1. Create a signal to hold the role state
  readonly userRole = signal<string>('Loading...');
  readonly feedbackMessage = signal('');

  constructor() {
    // 2. Reactively fetch the role whenever the currentUser signal updates
    effect(() => {
      const user = this.currentUser();
      if (user?.uid) {
        this.authService.getUserRole(user.uid).then(role => {
          this.userRole.set(role || 'did not manage to fetch role');
        }).catch(() => {
          this.userRole.set('did not manage to fetch role');
        });
      } else {
        this.userRole.set('guest');
      }
    });
  }
}