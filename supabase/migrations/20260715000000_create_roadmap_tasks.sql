create table if not exists public.roadmap_tasks (
  id uuid primary key default gen_random_uuid(),
  step_id uuid not null references public.roadmap_steps(id) on delete cascade,
  roadmap_id uuid not null references public.career_roadmaps(id) on delete cascade,
  analysis_id uuid not null,
  user_id uuid not null,
  day_name text not null,
  task_order integer not null,
  title text not null,
  estimated_minutes integer not null,
  status text not null default 'not_started',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint roadmap_tasks_day_name_check check (
    day_name in (
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
      'Sunday'
    )
  ),
  constraint roadmap_tasks_status_check check (
    status in ('not_started', 'completed')
  ),
  constraint roadmap_tasks_task_order_check check (task_order > 0),
  constraint roadmap_tasks_estimated_minutes_check check (estimated_minutes between 20 and 90)
);

create index if not exists roadmap_tasks_roadmap_id_idx
  on public.roadmap_tasks (roadmap_id);

create index if not exists roadmap_tasks_step_id_idx
  on public.roadmap_tasks (step_id);

create index if not exists roadmap_tasks_user_id_idx
  on public.roadmap_tasks (user_id);

alter table public.roadmap_tasks enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'roadmap_tasks'
      and policyname = 'Users can select their own roadmap tasks'
  ) then
    create policy "Users can select their own roadmap tasks"
      on public.roadmap_tasks
      for select
      using (auth.uid() = user_id);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'roadmap_tasks'
      and policyname = 'Users can update their own roadmap tasks'
  ) then
    create policy "Users can update their own roadmap tasks"
      on public.roadmap_tasks
      for update
      using (auth.uid() = user_id)
      with check (auth.uid() = user_id);
  end if;
end $$;
