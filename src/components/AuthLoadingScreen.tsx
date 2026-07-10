import { Sparkles } from 'lucide-react';

export default function AuthLoadingScreen() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="text-center">
        <span className="mx-auto flex size-12 items-center justify-center rounded-md bg-brand-600 text-white">
          <Sparkles className="size-6" />
        </span>
        <p className="mt-4 text-sm font-semibold text-slate-700">Loading CareerPilot AI...</p>
      </div>
    </main>
  );
}
