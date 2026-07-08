import { Bell, BriefcaseBusiness, ShieldCheck, UserCircle } from 'lucide-react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import Textarea from '../components/ui/Textarea';
import { useAuth } from '../hooks/useAuth';
import { profilePreferences } from '../data/mockData';

export default function ProfilePage() {
  const { user } = useAuth();
  const fullName = user?.fullName ?? 'CareerPilot User';
  const email = user?.email ?? 'user@example.com';

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-brand-700">Account Settings</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">Profile</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Keep your career context up to date so future analyses can stay focused on your goals.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
        <Card className="p-5">
          <UserCircle className="size-12 text-brand-700" />
          <h2 className="mt-4 text-xl font-semibold text-slate-950">{fullName}</h2>
          <p className="mt-1 text-sm text-slate-500">{email}</p>
          <div className="mt-5 rounded-md bg-slate-50 px-4 py-3">
            <p className="text-sm font-semibold text-slate-950">Current focus</p>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Preparing for Product Manager applications in AI-enabled SaaS products.
            </p>
          </div>
        </Card>

        <Card className="p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-3">
            <BriefcaseBusiness className="size-6 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">Career Preferences</h2>
          </div>
          <form className="grid gap-5 md:grid-cols-2">
            <Input label="Full Name" name="name" defaultValue={fullName} />
            <Input label="Email" name="email" type="email" defaultValue={email} />
            <Input label="Current Role" name="currentRole" defaultValue="Career Transitioner" />
            <Input label="Target Role" name="targetRole" defaultValue="Product Manager" />
            <div className="md:col-span-2">
              <Textarea
                label="Career Goals"
                name="goals"
                defaultValue="Move into a product role that combines customer research, analytics, and AI-enabled workflow design."
              />
            </div>
            <div className="md:col-span-2">
              <Button type="submit">Save Profile</Button>
            </div>
          </form>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="text-lg font-semibold text-slate-950">Career Profile Snapshot</h2>
          <div className="mt-4 space-y-3">
            {profilePreferences.map((item) => (
              <div key={item} className="rounded-md bg-slate-50 px-4 py-3 text-sm text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold text-slate-950">Account Settings</h2>
          <div className="mt-4 space-y-3">
            {[
              { label: 'Email notifications', value: 'Enabled', icon: Bell },
              { label: 'Data export', value: 'Available soon', icon: ShieldCheck },
              { label: 'Workspace plan', value: 'Starter', icon: BriefcaseBusiness },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="flex items-center justify-between rounded-md bg-slate-50 px-4 py-3">
                  <span className="flex items-center gap-3 text-sm font-medium text-slate-700">
                    <Icon className="size-4 text-brand-700" />
                    {item.label}
                  </span>
                  <span className="text-sm font-semibold text-slate-950">{item.value}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
