import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { FirebaseAuthService } from '../app/firebase-auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './register.html',
  styleUrl: './register.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterPage {
  private readonly authService = inject(FirebaseAuthService);
  private readonly router = inject(Router);

  readonly registerForm = new FormGroup({
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    password: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    /*To delete if we want to remove the possibility to create admin users from the register page*/
    role: new FormControl<'user' | 'admin'>('user', { nonNullable: true }),
  });

  readonly authMessage = signal('');
  readonly isSubmitting = signal(false);
  readonly isRegistered = signal(false);

  async submitRegister(): Promise<void> {
    if (this.registerForm.invalid) {
      this.authMessage.set('Please enter a valid email and password.');
      return;
    }

    const { email, password, role } = this.registerForm.getRawValue();
    this.isSubmitting.set(true);

    try {
      // 2. Await account creation & capture returned user credential
      const userCredential = await this.authService.signUp(email, password);
      const newUid = userCredential?.user?.uid;

      if (!newUid) {
        throw new Error('User creation failed: No valid UID returned from Firebase.');
      }

      // 3. Await role assignment using the confirmed UID
      await this.authService.assignUserRole(email, newUid, role);

      this.isRegistered.set(true);
      this.authMessage.set('Account created successfully. Welcome aboard.');
    } catch (error: unknown) {
      this.authMessage.set(this.getFriendlyMessage(error));
    } finally {
      this.isSubmitting.set(false);
    }
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
    this.authMessage.set('');
  }

  private getFriendlyMessage(error: unknown): string {
    const message = error instanceof Error ? error.message : 'Registration failed.';

    if (message.includes('auth/invalid-email')) {
      return 'Please enter a valid email address.';
    }

    if (message.includes('auth/weak-password')) {
      return 'Choose a stronger password with at least 6 characters.';
    }

    if (message.includes('auth/email-already-in-use')) {
      return 'This email is already registered. Try signing in instead.';
    }

    return 'Registration failed. Verify your Firebase configuration and try again.';
  }
}
