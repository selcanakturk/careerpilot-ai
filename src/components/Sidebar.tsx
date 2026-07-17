import {
  FileUp,
  History,
  LayoutDashboard,
  LogOut,
  BriefcaseBusiness,
  User,
  X,
} from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

type SidebarProps = {
  isOpen: boolean;
  onClose: () => void;
};

const navItems = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Upload CV', to: '/upload-cv', icon: FileUp },
  { label: 'Jobs', to: '/jobs', icon: BriefcaseBusiness },
  { label: 'History', to: '/history', icon: History },
  { label: 'Profile', to: '/profile', icon: User },
];

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    const result = await logout();

    if (!result.error) {
      onClose();
      navigate('/');
    }
  };

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-slate-950/30 transition lg:hidden ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform lg:sticky lg:top-16 lg:z-20 lg:h-[calc(100vh-4rem)] lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5 lg:hidden">
          <span className="font-semibold text-slate-950">Navigation</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="inline-flex size-9 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100"
          >
            <X className="size-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.label}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition ${
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
                  }`
                }
              >
                <Icon className="size-5" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-slate-200 p-3">
          <button
            type="button"
            onClick={handleLogout}
            className="flex min-h-11 w-full items-center gap-3 rounded-md px-3 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-950"
          >
            <LogOut className="size-5" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
