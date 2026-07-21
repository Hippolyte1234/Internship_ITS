import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { initializeApp } from 'firebase/app';
import { createUserWithEmailAndPassword, getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged, type User } from 'firebase/auth';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class FirebaseAuthService {
  private readonly router = inject(Router);
  private readonly app = initializeApp(environment.firebaseConfig);
  private readonly auth = getAuth(this.app);

  readonly currentUser = signal<User | null>(null);

  constructor() {
    onAuthStateChanged(this.auth, (user) => {
      this.currentUser.set(user);
    });
  }

  async signIn(email: string, password: string): Promise<void> {
    await signInWithEmailAndPassword(this.auth, email, password);
    await this.router.navigate(['/dashboard']);
  }

  async signUp(email: string, password: string): Promise<void> {
    await createUserWithEmailAndPassword(this.auth, email, password);
    await this.router.navigate(['/dashboard']);
  }

  async signOutUser(): Promise<void> {
    try {
      await signOut(this.auth);
    } finally {
      this.currentUser.set(null);
      await this.router.navigate(['/login']);
    }
  }
}
