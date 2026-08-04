import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { initializeApp } from 'firebase/app';
import { createUserWithEmailAndPassword, getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged, type User, UserCredential } from 'firebase/auth';
import { environment } from '../environments/environment';
import { getFirestore, doc, getDoc, setDoc } from 'firebase/firestore';

@Injectable({ providedIn: 'root' })
export class FirebaseAuthService {
  private readonly router = inject(Router);
  private readonly app = initializeApp(environment.firebaseConfig);
  private readonly db = getFirestore(this.app);
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

  async signUp(email: string, password: string): Promise<UserCredential> {
    return await createUserWithEmailAndPassword(this.auth, email, password);
    await this.router.navigate(['/dashboard']);
  }

  async assignUserRole(email: string, uid: string, assignedRole: string): Promise<void> {
    try {
      const userDocRef = doc(this.db, 'users', uid);

      const username = email.split('@')[0]; // Store the email as the username in Firestore
      
      await setDoc(userDocRef, { role: assignedRole }, { merge: true });
      await setDoc(userDocRef, { username: username }, { merge: true });
      
      console.log(`Successfully assigned role '${assignedRole}' to user ${uid}`);
    } catch (error) {
      console.error("Error writing role to Firestore:", error);
      throw error;
    }
  }

  async getUserRole(uid: string): Promise<string | null> {
    const userDocRef = doc(this.db, 'users', uid);

    const userDoc = await getDoc(userDocRef);
    return userDoc.exists() ? userDoc.data()?.['role'] || null : null;
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
