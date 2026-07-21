import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { FirebaseAuthService } from '../app/firebase-auth.service';

interface LoginFormValue {
  email: string;
  password: string;
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginPage {
  private readonly authService = inject(FirebaseAuthService);
  private readonly router = inject(Router);

  readonly loginForm = new FormGroup({
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    password: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
  });

  readonly isLoggedIn = signal(false);
  readonly authMessage = signal('');
  readonly currentUserName = signal('');
  readonly isSubmitting = signal(false);

  submitLogin(): void {
    if (this.loginForm.invalid) {
      this.authMessage.set('Please enter a valid email and password.');
      return;
    }

    const { email, password } = this.loginForm.getRawValue() as LoginFormValue;
    this.isSubmitting.set(true);

    this.authService
      .signIn(email, password)
      .then(() => {
        this.isLoggedIn.set(true);
        this.authMessage.set('Signed in successfully.');
        this.currentUserName.set(email.split('@')[0].replace(/\./g, ' '));
      })
      .catch((error: unknown) => {
        this.authMessage.set(this.getFriendlyMessage(error));
      })
      .finally(() => {
        this.isSubmitting.set(false);
      });
  }

  goToRegister(): void {
    this.router.navigate(['/register']);
    this.authMessage.set('');
  }

  goToDashboard(): void {
    this.router.navigate(['/dashboard']);
  }

  resetLogin(): void {
    this.isLoggedIn.set(false);
    this.authMessage.set('');
    this.currentUserName.set('');
    this.isSubmitting.set(false);
    this.loginForm.reset({ email: '', password: '' });
  }

  private getFriendlyMessage(error: unknown): string {
    const message = error instanceof Error ? error.message : 'Authentication failed.';

    if (message.includes('auth/invalid-email')) {
      return 'Please enter a valid email address.';
    }

    if (message.includes('auth/weak-password')) {
      return 'Choose a stronger password with at least 6 characters.';
    }

    if (message.includes('auth/email-already-in-use')) {
      return 'This email is already registered. Try signing in instead.';
    }

    if (message.includes('auth/user-not-found') || message.includes('auth/wrong-password')) {
      return 'These credentials do not match any account.';
    }

    if (message.includes('Firebase config')) {
      return message;
    }

    return 'Authentication failed. Verify your Firebase configuration and try again.';
  }
}
