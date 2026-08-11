import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LegalService {
  private apiUrl = 'http://localhost:8000/api/cases';

  constructor(private http: HttpClient) {}

  private getHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      headers: new HttpHeaders({
        'Authorization': token ? `Bearer ${token}` : ''
      })
    };
  }

  // Clients
  getClients(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/clients/`, this.getHeaders());
  }

  createClient(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/clients/`, data, this.getHeaders());
  }

  // Cases
  getCases(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/cases/`, this.getHeaders());
  }

  createCase(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/cases/`, data, this.getHeaders());
  }

  // Schedules
  getSchedules(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/schedules/`, this.getHeaders());
  }

  createSchedule(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/schedules/`, data, this.getHeaders());
  }

  // Documents
  getDocuments(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/documents/`, this.getHeaders());
  }

  uploadDocument(caseId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('case_file', caseId.toString());
    formData.append('file', file);

    const token = localStorage.getItem('access_token');
    // For FormData, let HttpClient set the boundary, so do NOT set Content-Type header manually
    const uploadHeaders = {
      headers: new HttpHeaders({
        'Authorization': token ? `Bearer ${token}` : ''
      })
    };
    return this.http.post<any>(`${this.apiUrl}/documents/upload/`, formData, uploadHeaders);
  }

  // AI Multi-Agent RAG Drafting
  generateDraft(prompt: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/draft/`, { user_prompt: prompt }, this.getHeaders());
  }
}
