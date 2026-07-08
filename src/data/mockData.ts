import {
  BarChart3,
  BookOpenCheck,
  BriefcaseBusiness,
  CalendarClock,
  CheckCircle2,
  FileText,
  MessageSquareText,
  Target,
  TrendingUp,
} from 'lucide-react';

export const stats = [
  { label: 'Average Match Score', value: '82%', change: '+8% from last review', icon: BarChart3 },
  { label: 'Role-Aligned Skills', value: '18', change: '6 priority gaps found', icon: Target },
  { label: 'Roadmap Actions', value: '24', change: '9 completed this month', icon: BookOpenCheck },
  { label: 'Interview Prompts', value: '32', change: '12 tailored to your CV', icon: MessageSquareText },
];

export const recentAnalyses = [
  {
    id: '1',
    role: 'Product Manager',
    score: 82,
    date: 'Jul 5, 2026',
    status: 'Ready to review',
    summary: 'Strong product discovery background with gaps in metrics ownership and roadmap tradeoffs.',
  },
  {
    id: '2',
    role: 'UX Researcher',
    score: 76,
    date: 'Jun 29, 2026',
    status: 'Needs refinement',
    summary: 'Research process is clear, but portfolio outcomes need stronger business context.',
  },
  {
    id: '3',
    role: 'Data Analyst',
    score: 88,
    date: 'Jun 18, 2026',
    status: 'Application ready',
    summary: 'Well-aligned analytics experience with clear evidence of dashboarding and stakeholder impact.',
  },
];

export const dashboardSkillSummary = [
  { label: 'Product Discovery', value: 86 },
  { label: 'Analytics & Metrics', value: 68 },
  { label: 'Stakeholder Management', value: 78 },
];

export const roadmapProgress = [
  { label: 'CV positioning', done: 3, total: 4 },
  { label: 'Portfolio evidence', done: 1, total: 3 },
  { label: 'Interview practice', done: 2, total: 5 },
];

export const strengths = [
  'Clear experience translating customer needs into product requirements and delivery plans.',
  'Strong cross-functional collaboration across design, operations, and engineering-adjacent teams.',
  'Relevant examples of process improvement, discovery work, and stakeholder communication.',
];

export const weaknesses = [
  'Business impact is often described qualitatively instead of being supported by metrics.',
  'Prioritization decisions need clearer examples of constraints, tradeoffs, and success criteria.',
  'Analytics experience is present but should be connected to product KPIs more directly.',
];

export const skillGaps = [
  'Quantify product outcomes with metrics such as activation, retention, revenue impact, or cycle-time reduction.',
  'Add stronger examples of roadmap prioritization, including tradeoffs, constraints, and stakeholder alignment.',
  'Show clearer evidence of analytics fluency through SQL, experiment design, dashboard ownership, or KPI reviews.',
  'Connect customer research to product decisions with one concrete discovery-to-delivery case study.',
  'Clarify leadership scope by naming team size, decision ownership, and cross-functional partners.',
];

export const roadmap = [
  {
    title: 'Refine the executive summary',
    detail: 'Position your background around product discovery, measurable outcomes, and cross-functional delivery.',
    icon: FileText,
  },
  {
    title: 'Strengthen impact bullets',
    detail: 'Rewrite three recent role bullets using action, business context, metric, and result.',
    icon: BriefcaseBusiness,
  },
  {
    title: 'Close analytics gaps',
    detail: 'Prepare one SQL or dashboard example that explains the question, analysis, decision, and outcome.',
    icon: TrendingUp,
  },
  {
    title: 'Run an interview sprint',
    detail: 'Practice product sense, prioritization, stakeholder management, and behavioral stories before applying.',
    icon: CalendarClock,
  },
];

export const cvImprovements = [
  {
    title: 'Rewrite the headline',
    detail: 'Lead with the target role and strongest proof point, not a generic summary statement.',
  },
  {
    title: 'Add measurable outcomes',
    detail: 'Include metrics such as adoption, retention, cycle time, cost savings, or customer satisfaction.',
  },
  {
    title: 'Group relevant tools',
    detail: 'Create a concise skills section for analytics, product discovery, roadmap, and collaboration tools.',
  },
  {
    title: 'Tighten role descriptions',
    detail: 'Remove low-impact responsibilities and prioritize achievements that map to the target job.',
  },
];

export const interviewQuestions = [
  'Walk me through a product decision you made with incomplete data. What did you prioritize and why?',
  'How would you evaluate whether a new onboarding flow improves activation without hurting retention?',
  'Tell me about a time you aligned design, engineering, and business stakeholders around a difficult tradeoff.',
  'Describe a customer insight that changed your roadmap. How did you validate it before delivery?',
  'What metrics would you track for an AI-powered career coaching feature after launch?',
  'Give an example of a project where the final result differed from the original request. What changed?',
];

export const landingHowItWorks = [
  {
    title: 'Upload your CV',
    description: 'Start with your latest CV and add the role you want to target.',
  },
  {
    title: 'Review the analysis',
    description: 'See match score, strengths, weak spots, and missing evidence.',
  },
  {
    title: 'Follow the roadmap',
    description: 'Work through focused actions for CV, skills, portfolio, and interviews.',
  },
];

export const landingReasons = [
  {
    title: 'Built around role fit',
    description: 'Feedback is framed around the job you want, not generic career advice.',
    icon: Target,
  },
  {
    title: 'Actionable by design',
    description: 'Every insight points to a next step you can use before applying.',
    icon: CheckCircle2,
  },
  {
    title: 'Prepared for interviews',
    description: 'Practice questions connect your CV evidence to realistic hiring conversations.',
    icon: MessageSquareText,
  },
];

export const profilePreferences = [
  'Target role: Product Manager',
  'Preferred industries: SaaS, AI tools, Future of Work',
  'Seniority level: Associate to Mid-level',
  'Application focus: CV quality, portfolio proof, interview confidence',
];
