import { TestBed } from '@angular/core/testing';
import { LoginPage } from './login';

describe('LoginPage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginPage],
    }).compileComponents();
  });

  it('should render the sign-in heading', () => {
    const fixture = TestBed.createComponent(LoginPage);
    fixture.detectChanges();

    const heading = fixture.nativeElement.querySelector('h1');
    expect(heading?.textContent).toContain('Sign in');
  });

  it('should offer a create-account toggle', () => {
    const fixture = TestBed.createComponent(LoginPage);
    fixture.detectChanges();

    const toggleButton = fixture.nativeElement.querySelector('button.secondary');
    expect(toggleButton?.textContent).toContain('Create an account');
  });

  it('should not expose an admin role option in the regular account creation form', () => {
    const fixture = TestBed.createComponent(LoginPage);
    fixture.componentInstance.toggleMode();
    fixture.detectChanges();

    const roleSelect = fixture.nativeElement.querySelector('select');
    expect(roleSelect).toBeNull();
  });
});
