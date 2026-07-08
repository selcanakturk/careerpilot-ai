import { Menu, Sparkles } from 'lucide-react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Button from './ui/Button';

type NavbarProps = {
  onMenuClick?: () => void;
};

const publicLinks = [
  { label: 'Features', to: '/#features' },
];

export default function Navbar({ onMenuClick }: NavbarProps) {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          {onMenuClick && (
            <button
              type="button"
              aria-label="Open navigation"
              onClick={onMenuClick}
              className="inline-flex size-10 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 lg:hidden"
            >
              <Menu className="size-5" />
            </button>
          )}
          <Link to="/" className="flex items-center gap-2 font-bold text-slate-950">
            <span className="flex size-9 items-center justify-center rounded-md bg-brand-600 text-white">
              <Sparkles className="size-5" />
            </span>
            <span>CareerPilot AI</span>
          </Link>
        </div>

        {!onMenuClick && !isAuthenticated && (
          <nav className="hidden items-center gap-7 text-sm font-medium text-slate-600 md:flex">
            {publicLinks.map((link) => (
              <NavLink key={link.label} to={link.to} className="hover:text-slate-950">
                {link.label}
              </NavLink>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard">
                <Button variant="ghost" className="hidden sm:inline-flex">
                  Dashboard
                </Button>
              </Link>
              <Button onClick={handleLogout}>Sign Out</Button>
            </>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost" className="hidden sm:inline-flex">
                  Log In
                </Button>
              </Link>
              <Link to="/register">
                <Button>Get Started</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
