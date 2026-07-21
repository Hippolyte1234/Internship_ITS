import { Routes } from '@angular/router';
import { LoginPage } from '../login/login';
import { RegisterPage } from '../register/register';
import { Appbar } from './appbar/appbar';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginPage },
  { path: 'register', component: RegisterPage },
  {
    path: '',
    component: Appbar,
    children: [
      { path: 'dashboard', loadComponent: () => import('../dashboard/dashboard').then((m) => m.DashboardPage) },
      { path: 'settings', loadComponent: () => import('../settings/settings').then((m) => m.SettingsPanel) },
      { path: 'chatbot', loadComponent: () => import('../chatbot/chatbot').then((m) => m.ChatbotComponent) }
    ],
  },
  { path: '**', redirectTo: '/login' },
];
