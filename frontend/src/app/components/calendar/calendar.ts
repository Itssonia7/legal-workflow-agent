import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LegalService } from '../../services/legal.service';

@Component({
  selector: 'app-calendar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './calendar.html',
  styleUrl: './calendar.css'
})
export class Calendar implements OnInit {
  cases: any[] = [];
  schedules: any[] = [];

  // Form state
  newSchedule = { case_file: '', hearing_date: '', description: '', court_room: '' };
  showForm = false;

  constructor(private legalService: LegalService) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.legalService.getCases().subscribe({
      next: (data) => this.cases = data,
      error: (err) => console.error('Error fetching cases:', err)
    });

    this.legalService.getSchedules().subscribe({
      next: (data) => this.schedules = data,
      error: (err) => console.error('Error fetching schedules:', err)
    });
  }

  addSchedule(): void {
    if (!this.newSchedule.case_file || !this.newSchedule.hearing_date) return;
    this.legalService.createSchedule(this.newSchedule).subscribe({
      next: (s) => {
        this.schedules.push(s);
        this.newSchedule = { case_file: '', hearing_date: '', description: '', court_room: '' };
        this.showForm = false;
        this.loadData(); // Reload to sort correctly and resolve fields
      },
      error: (err) => alert('Failed to schedule hearing: ' + JSON.stringify(err.error))
    });
  }
}
