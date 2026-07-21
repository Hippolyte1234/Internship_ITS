import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FirebaseAuthService } from '../app/firebase-auth.service';
import { Appbar } from "../app/appbar/appbar";
import { AiChartComponent } from '../graphics/graphics_controller';


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

  readonly userRole = computed(() => {
    const email = this.authService.currentUser()?.email ?? '';
    const storedRole = email ? localStorage.getItem(`dashboard-account-role:${email}`) : null;
    return storedRole === 'admin' ? 'admin' : 'user';
  });

  

readonly feedbackMessage = signal('');


    
}
