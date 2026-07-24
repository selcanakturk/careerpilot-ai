import {
  ArrowRight,
  Bot,
  BrainCircuit,
  BriefcaseBusiness,
  FileSearch,
  ListChecks,
  MessagesSquare,
  Sparkles,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';

const features = [
  {
    title: 'AI CV Analysis',
    description: 'Evaluate your CV’s clarity, strengths, weaknesses, ATS readiness, and missing skills.',
    icon: FileSearch,
  },
  {
    title: 'AI Job Match',
    description: 'Compare your CV with real job postings and understand your compatibility score.',
    icon: BriefcaseBusiness,
  },
  {
    title: 'AI CV Optimizer',
    description: 'Generate a focused, ATS-friendly rewrite tailored to a selected job.',
    icon: Sparkles,
  },
  {
    title: 'AI Career Copilot',
    description: 'Ask personalized career questions using your CV, roadmap, profile, and job-match context.',
    icon: BrainCircuit,
  },
  {
    title: 'Personalized Roadmap',
    description: 'Turn your gaps into a practical weekly learning and application plan.',
    icon: ListChecks,
  },
  {
    title: 'Interview Preparation',
    description: 'Practice role-specific questions based on your experience and target position.',
    icon: MessagesSquare,
  },
];

const howItWorks = [
  {
    title: 'Upload your CV',
    description: 'Add your current CV so CareerPilot AI can understand your background and target direction.',
  },
  {
    title: 'Analyze strengths and gaps',
    description: 'Get a structured report with readiness score, strengths, weaknesses, and missing skills.',
  },
  {
    title: 'Match with real jobs',
    description: 'Compare your CV against saved or discovered job postings and see what fits.',
  },
  {
    title: 'Optimize your application',
    description: 'Tailor your CV for a selected role with focused, ATS-friendly improvements.',
  },
  {
    title: 'Ask Career Copilot',
    description: 'Use Copilot for practical guidance based on your CV, roadmap, jobs, and profile context.',
  },
];

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  const scrollToFeatures = () => {
    document.getElementById('features')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main>
        <section className="overflow-hidden bg-white">
          <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:px-8 lg:py-20">
            <div>
              <p className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-brand-700">
                AI-powered career assistant
              </p>
              <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl lg:text-6xl">
                One AI workspace for every job application.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
                Analyze your CV, compare it with real job postings, optimize each application,
                and get personalized guidance from your AI Career Copilot.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link to={isAuthenticated ? '/dashboard' : '/register'}>
                  <Button className="w-full sm:w-auto">
                    {isAuthenticated ? 'Go to Dashboard' : 'Get Started'}
                    <ArrowRight className="size-4" />
                  </Button>
                </Link>
                <Button variant="secondary" className="w-full sm:w-auto" onClick={scrollToFeatures}>
                  Explore Features
                </Button>
              </div>
              <div className="mt-8 grid gap-4 text-sm text-slate-600 sm:grid-cols-3">
                {['AI CV Analysis', 'Job Match', 'Career Copilot'].map((item) => (
                  <div key={item} className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
                    <span className="font-semibold text-slate-950">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="rounded-lg border border-slate-200 bg-slate-950 p-4 shadow-soft">
                <div className="mb-4 flex items-center gap-2">
                  <span className="size-3 rounded-full bg-rose-400" />
                  <span className="size-3 rounded-full bg-amber-300" />
                  <span className="size-3 rounded-full bg-emerald-400" />
                </div>
                <div className="rounded-md bg-white p-5">
                  <div className="mb-5 flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-slate-500">Workspace preview</p>
                      <h2 className="mt-1 text-xl font-bold text-slate-950">Application intelligence</h2>
                    </div>
                    <span className="rounded-md bg-brand-50 px-3 py-1 text-sm font-semibold text-brand-700">
                      AI workspace
                    </span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-md bg-slate-50 p-4">
                      <p className="text-sm font-semibold text-slate-600">Job Match</p>
                      <p className="mt-2 text-4xl font-bold text-slate-950">72%</p>
                      <p className="mt-2 text-sm leading-6 text-slate-600">Strong API and backend fit.</p>
                    </div>
                    <div className="rounded-md bg-brand-50 p-4">
                      <p className="text-sm font-semibold text-brand-700">Estimated after optimization</p>
                      <p className="mt-2 text-4xl font-bold text-brand-800">88%</p>
                      <p className="mt-2 text-sm leading-6 text-slate-700">CV rewritten for the selected role.</p>
                    </div>
                  </div>
                  <div className="mt-3 rounded-md border border-slate-100 bg-slate-50 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Bot className="size-4 text-brand-700" />
                      <p className="text-sm font-semibold text-slate-950">Career Copilot</p>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-600">
                      “Your strongest next step is to improve Docker and cloud deployment skills.”
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-14 sm:px-6 lg:px-8">
          <div className="mb-8 max-w-2xl">
            <p className="text-sm font-semibold text-brand-700">Platform Features</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
              Every core workflow for stronger applications.
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card key={feature.title} className="p-5 transition hover:-translate-y-1 hover:shadow-lg">
                  <Icon className="mb-4 size-7 text-brand-700" />
                  <h3 className="text-base font-semibold text-slate-950">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{feature.description}</p>
                </Card>
              );
            })}
          </div>
        </section>

        <section className="bg-white">
          <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
            <div className="mb-8 max-w-2xl">
              <p className="text-sm font-semibold text-brand-700">How It Works</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
                From one CV upload to a stronger application.
              </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {howItWorks.map((step, index) => (
                <div key={step.title} className="rounded-lg border border-slate-200 bg-slate-50 p-5">
                  <span className="flex size-10 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
                    {index + 1}
                  </span>
                  <h3 className="mt-4 text-lg font-semibold text-slate-950">{step.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
