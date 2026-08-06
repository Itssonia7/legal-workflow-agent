import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CaseDashboard } from './case-dashboard';

describe('CaseDashboard', () => {
  let component: CaseDashboard;
  let fixture: ComponentFixture<CaseDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CaseDashboard],
    }).compileComponents();

    fixture = TestBed.createComponent(CaseDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
