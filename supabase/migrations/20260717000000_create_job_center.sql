create table if not exists public.job_postings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  company_name text not null,
  location text,
  employment_type text,
  work_mode text,
  source_url text,
  description text not null,
  status text not null default 'saved',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint job_postings_status_check check (status in ('saved', 'analyzing', 'analyzed', 'archived')),
  constraint job_postings_employment_type_check check (
    employment_type is null or employment_type in ('full_time', 'part_time', 'internship', 'contract', 'freelance')
  ),
  constraint job_postings_work_mode_check check (
    work_mode is null or work_mode in ('onsite', 'hybrid', 'remote')
  )
);

create table if not exists public.job_matches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  job_posting_id uuid not null references public.job_postings(id) on delete cascade,
  analysis_id uuid not null references public.cv_analyses(id) on delete cascade,
  match_score integer not null check (match_score between 0 and 100),
  summary text not null,
  matched_skills jsonb not null default '[]'::jsonb,
  missing_skills jsonb not null default '[]'::jsonb,
  strengths jsonb not null default '[]'::jsonb,
  risks jsonb not null default '[]'::jsonb,
  recommendations jsonb not null default '[]'::jsonb,
  application_readiness text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint job_matches_application_readiness_check check (application_readiness in ('low', 'medium', 'high')),
  constraint job_matches_job_posting_analysis_unique unique (job_posting_id, analysis_id)
);

create index if not exists job_postings_user_id_idx on public.job_postings(user_id);
create index if not exists job_postings_status_idx on public.job_postings(status);
create index if not exists job_matches_user_id_idx on public.job_matches(user_id);
create index if not exists job_matches_job_posting_id_idx on public.job_matches(job_posting_id);
create index if not exists job_matches_analysis_id_idx on public.job_matches(analysis_id);

alter table public.job_postings enable row level security;
alter table public.job_matches enable row level security;

create policy "Users can select own job postings"
  on public.job_postings for select
  to authenticated
  using (auth.uid() = user_id);

create policy "Users can insert own job postings"
  on public.job_postings for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "Users can update own job postings"
  on public.job_postings for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete own job postings"
  on public.job_postings for delete
  to authenticated
  using (auth.uid() = user_id);

create policy "Users can select own job matches"
  on public.job_matches for select
  to authenticated
  using (auth.uid() = user_id);

create policy "Users can insert own job matches"
  on public.job_matches for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "Users can update own job matches"
  on public.job_matches for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete own job matches"
  on public.job_matches for delete
  to authenticated
  using (auth.uid() = user_id);

grant select, insert, update, delete on public.job_postings to authenticated;
grant select, insert, update, delete on public.job_matches to authenticated;
grant all on public.job_postings to service_role;
grant all on public.job_matches to service_role;
