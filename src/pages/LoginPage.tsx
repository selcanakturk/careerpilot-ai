import type { FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import { useAuth } from '../hooks/useAuth';

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname ?? '/dashboard';

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    login();
    navigate(from, { replace: true });
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
        <h1 className="mt-8 text-2xl font-bold text-slate-950">Welcome Back</h1>
        <p className="mt-2 text-sm text-slate-600">
          Access your workspace and continue improving your career plan.
        </p>
        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          <Input label="Email" name="email" type="email" placeholder="you@example.com" />
          <Input label="Password" name="password" type="password" placeholder="••••••••" />
          <Button type="submit" className="w-full">
            Log In
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-600">
          New here?{' '}
          <Link to="/register" className="font-semibold text-brand-700 hover:text-brand-600">
            Create an Account
          </Link>
        </p>
      </Card>
    </main>
  );
}
