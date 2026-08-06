import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentVault } from './document-vault';

describe('DocumentVault', () => {
  let component: DocumentVault;
  let fixture: ComponentFixture<DocumentVault>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DocumentVault],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentVault);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
