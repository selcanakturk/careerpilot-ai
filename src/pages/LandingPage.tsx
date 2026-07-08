import { ArrowRight, BrainCircuit, FileSearch, ListChecks, MessagesSquare } from 'lucide-react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { landingHowItWorks, landingReasons } from '../data/mockData';

const features = [
  {
    title: 'CV readiness analysis',
    description: 'Evaluate clarity, structure, achievement quality, and role alignment from one upload.',
    icon: FileSearch,
  },
  {
    title: 'Targeted skill gaps',
    description: 'Identify missing proof points, technical gaps, and positioning risks for your target role.',
    icon: BrainCircuit,
  },
  {
    title: 'Actionable roadmap',
    description: 'Turn feedback into practical next steps for your CV, portfolio, skills, and applications.',
    icon: ListChecks,
  },
  {
    title: 'Role-specific interview prep',
    description: 'Practice realistic questions shaped around your experience and target job description.',
    icon: MessagesSquare,
  },
];

export default function LandingPage() {
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
                CareerPilot AI for sharper applications and stronger interviews.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
                Upload your CV, choose a target role, and turn scattered career advice into a
                focused plan with match scoring, skill gap feedback, CV improvements, and mock
                interview prompts.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link to="/register">
                  <Button className="w-full sm:w-auto">
                    Get Started
                    <ArrowRight className="size-4" />
                  </Button>
                </Link>
                <Link to="/#features">
                  <Button variant="secondary" className="w-full sm:w-auto">
                    See Features
                  </Button>
                </Link>
              </div>
              <div className="mt-8 grid gap-4 text-sm text-slate-600 sm:grid-cols-3">
                {['CV scoring', 'Skill gap map', 'Interview prep'].map((item) => (
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
                      <h2 className="mt-1 text-xl font-bold text-slate-950">Career readiness flow</h2>
                    </div>
                    <span className="rounded-md bg-brand-50 px-3 py-1 text-sm font-semibold text-brand-700">
                      Private by default
                    </span>
                  </div>
                  <div className="space-y-3">
                    {[
                      ['1', 'Upload CV', 'Add a CV after signing in.'],
                      ['2', 'Choose target role', 'Tell CareerPilot AI what you are applying for.'],
                      ['3', 'Review guidance', 'See strengths, gaps, roadmap, and interview prompts.'],
                    ].map(([step, title, detail]) => (
                      <div key={title} className="flex gap-3 rounded-md bg-slate-50 px-4 py-3">
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
                          {step}
                        </span>
                        <div>
                          <p className="text-sm font-semibold text-slate-950">{title}</p>
                          <p className="mt-1 text-sm leading-6 text-slate-600">{detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-5 rounded-md bg-slate-50 p-4">
                    <p className="text-sm font-semibold text-slate-950">No personal data on the public page</p>
                    <p className="mt-1 text-sm leading-6 text-slate-600">
                      Scores and analysis details only appear inside the authenticated workspace.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <div className="mb-8 max-w-2xl">
            <p className="text-sm font-semibold text-brand-700">Platform Features</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
              Everything you need before you apply.
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
                From CV upload to interview-ready plan.
              </h2>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              {landingHowItWorks.map((step, index) => (
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

        <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
            <div>
              <p className="text-sm font-semibold text-brand-700">Why CareerPilot AI?</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
                Designed for candidates who want specific, usable feedback.
              </h2>
              <p className="mt-4 text-sm leading-6 text-slate-600">
                CareerPilot AI keeps the process practical: understand what is working, what is
                missing, and what to improve before your next application.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {landingReasons.map((reason) => {
                const Icon = reason.icon;
                return (
                  <Card key={reason.title} className="p-5">
                    <Icon className="size-6 text-brand-700" />
                    <h3 className="mt-4 font-semibold text-slate-950">{reason.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{reason.description}</p>
                  </Card>
                );
              })}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
