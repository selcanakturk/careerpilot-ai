import { type FormEvent, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import { useAuth } from '../hooks/useAuth';
import { getFormValue } from '../utils/form';

export default function RegisterPage() {
  const { isAuthenticated, register } = useAuth();
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const fullName = getFormValue(event, 'name');
    const email = getFormValue(event, 'email');
    const password = getFormValue(event, 'password');

    setErrorMessage('');
    setInfoMessage('');

    if (!fullName || !email || !password) {
      setErrorMessage('Please fill in all required fields.');
      return;
    }

    setIsSubmitting(true);

    const result = await register({ fullName, email, password });

    setIsSubmitting(false);

    if (result.error) {
      setErrorMessage(result.error);
      return;
    }

    if (result.message) {
      setInfoMessage(result.message);
      return;
    }

    navigate('/dashboard', { replace: true });
  };

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <Card className="w-full max-w-md p-6 sm:p-8">
        <Link to="/" className="text-xl font-bold text-slate-950">
          CareerPilot AI
        </Link>
        <h1 className="mt-8 text-2xl font-bold text-slate-950">Create Your Account</h1>
        <p className="mt-2 text-sm text-slate-600">
          Set up your workspace for CV analysis, skill gap feedback, and interview preparation.
        </p>
        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          <Input label="Full Name" name="name" type="text" placeholder="Alex Morgan" required />
          <Input label="Email" name="email" type="email" placeholder="you@example.com" required />
          <Input label="Password" name="password" type="password" placeholder="••••••••" required />
          {errorMessage && (
            <p className="rounded-md bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
              {errorMessage}
            </p>
          )}
          {infoMessage && (
            <p className="rounded-md bg-brand-50 px-4 py-3 text-sm font-medium text-brand-700">
              {infoMessage}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Creating Account...' : 'Create Account'}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-600">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-brand-700 hover:text-brand-600">
            Log In
          </Link>
        </p>
      </Card>
    </main>
  );
}
