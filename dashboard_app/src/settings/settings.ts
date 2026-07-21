import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FirebaseAuthService } from '../app/firebase-auth.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './settings.html',
  styleUrl: './settings.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPanel {
  private readonly authService = inject(FirebaseAuthService);

  readonly settingsForm = new FormGroup({
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    password: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.minLength(2)] }),
    role: new FormControl<'classic' | 'admin'>('classic', { nonNullable: true }),
  });

  readonly message = signal('');
  readonly isSubmitting = signal(false);
  readonly currentUser = computed(() => this.authService.currentUser());
  readonly userRole = computed(() => {
    const email = this.authService.currentUser()?.email ?? '';
    const storedRole = email ? localStorage.getItem(`dashboard-account-role:${email}`) : null;
    return storedRole === 'admin' ? 'admin' : 'user';
  });

  async createAccount(): Promise<void> {
    if (this.settingsForm.invalid) {
      this.message.set('Please enter a valid email and password.');
      return;
    }

    const { email, password, role } = this.settingsForm.getRawValue();
    this.isSubmitting.set(true);

    try {
      await this.authService.signUp(email, password);
      localStorage.setItem(`dashboard-account-role:${email}`, role);
      this.message.set(role === 'admin' ? 'Admin account created successfully.' : 'User account created successfully.');
    } catch (error) {
      this.message.set(this.getFriendlyMessage(error));
    } finally {
      this.isSubmitting.set(false);
    }
  }

  private getFriendlyMessage(error: unknown): string {
    const message = error instanceof Error ? error.message : 'Account creation failed.';

    if (message.includes('auth/weak-password')) {
      return 'Choose a stronger password with at least 6 characters.';
    }

    if (message.includes('auth/email-already-in-use')) {
      return 'This email is already registered. Try another address.';
    }

    return 'Account creation failed. Please verify your Firebase configuration.';
  }
}
