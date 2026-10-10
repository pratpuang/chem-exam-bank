-- Teaching app (teach.html) schema. Paste the whole file into Supabase -> SQL Editor -> Run.
-- Every row carries an owner = the logged-in user; RLS lets each user touch only their own rows,
-- so the publishable key in the page can't read anything without Prat's login.

create table if not exists students (
  id         text primary key,
  owner      uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name       text not null,
  grade      text,
  subj       text default 'chem',          -- chem | bio
  mode       text,                          -- ออนไลน์ | ออนไซต์
  rate       int,
  color      int default 0,
  slots      jsonb default '[]',            -- [[weekday,"HH:MM",hours], ...]
  goal       text,
  contact    text,
  map        text,                          -- chapter map, 14 chars: d done / n now / t todo / s skip
  feed       jsonb default '[]',            -- [[pro|con, "YYYY-MM-DD", text], ...]
  archived   boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists sessions (
  id         text primary key,
  owner      uuid not null default auth.uid() references auth.users(id) on delete cascade,
  who        text references students(id) on delete set null,
  date       date not null,
  time       text not null,                 -- "HH:MM" Bangkok time
  h          numeric not null default 1,
  rate       int,
  series     text,
  status     text not null default 'plan' check (status in ('plan','done','cancel')),
  paid       boolean default false,
  note       text default '',
  log        jsonb,                         -- {topic, hw}
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists sessions_date on sessions(owner, date);

-- everything else the app keeps (free hours, message templates, rates, holidays, monthly history, deadlines)
create table if not exists app_state (
  owner      uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  data       jsonb not null default '{}',
  updated_at timestamptz default now()
);

create or replace function touch() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists students_touch on students;  create trigger students_touch  before update on students  for each row execute function touch();
drop trigger if exists sessions_touch on sessions;  create trigger sessions_touch  before update on sessions  for each row execute function touch();
drop trigger if exists state_touch on app_state;    create trigger state_touch     before update on app_state for each row execute function touch();

alter table students  enable row level security;
alter table sessions  enable row level security;
alter table app_state enable row level security;
drop policy if exists own on students;  create policy own on students  for all to authenticated using (owner = auth.uid()) with check (owner = auth.uid());
drop policy if exists own on sessions;  create policy own on sessions  for all to authenticated using (owner = auth.uid()) with check (owner = auth.uid());
drop policy if exists own on app_state; create policy own on app_state for all to authenticated using (owner = auth.uid()) with check (owner = auth.uid());

-- 002: free-text notes per student (Notion's หัวข้อย่อย + หมายเหตุ land here)
alter table students add column if not exists notes text default '';

-- 003: student type (regular | adhoc | trial | stopped)
alter table students add column if not exists kind text default 'regular';
