import { Routes } from '@angular/router';
import { CaseDashboard } from './components/case-dashboard/case-dashboard';
import { Calendar } from './components/calendar/calendar';

export const routes: Routes = [
  { path: '', component: CaseDashboard },
  { path: 'calendar', component: Calendar },
];
