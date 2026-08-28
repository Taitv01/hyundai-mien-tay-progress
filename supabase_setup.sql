-- Chạy toàn bộ tệp này một lần trong Supabase SQL Editor.
create extension if not exists pgcrypto;

create table if not exists public.app_users (
    id uuid primary key default gen_random_uuid(),
    username text unique not null check (username = lower(username)),
    display_name text not null,
    password_hash text not null,
    role text not null default 'viewer' check (role in ('admin', 'editor', 'viewer')),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_login_at timestamptz
);

create table if not exists public.tasks (
    code text primary key,
    name text not null,
    area text not null,
    start_date date not null,
    end_date date not null,
    progress integer not null default 0 check (progress between 0 and 100),
    status text not null check (status in ('Chưa thực hiện', 'Đang thi công', 'Đã hoàn thiện', 'Dời tiến độ')),
    assignee text not null default '',
    notes text not null default '',
    sort_order integer not null default 0,
    updated_by uuid references public.app_users(id) on delete set null,
    updated_at timestamptz not null default now(),
    check (end_date >= start_date)
);

create table if not exists public.qcvn_items (
    stt integer primary key,
    group_name text not null,
    item_name text not null,
    is_ev boolean not null default false,
    assessment text not null check (assessment in ('Đạt', 'Đang thi công', 'Đang mua sắm', 'Đang đào tạo', 'Chưa đạt')),
    notes text not null default '',
    updated_by uuid references public.app_users(id) on delete set null,
    updated_at timestamptz not null default now()
);

create table if not exists public.progress_updates (
    id uuid primary key default gen_random_uuid(),
    task_code text not null references public.tasks(code) on delete cascade,
    progress integer not null check (progress between 0 and 100),
    status text not null,
    note text not null default '',
    updated_by uuid references public.app_users(id) on delete set null,
    updated_by_name text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.progress_photos (
    id uuid primary key default gen_random_uuid(),
    update_id uuid not null references public.progress_updates(id) on delete cascade,
    task_code text not null references public.tasks(code) on delete cascade,
    storage_path text unique not null,
    original_name text not null default '',
    uploaded_by uuid references public.app_users(id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_progress_updates_created_at
    on public.progress_updates(created_at desc);
create index if not exists idx_progress_updates_task_code
    on public.progress_updates(task_code, created_at desc);
create index if not exists idx_progress_photos_update_id
    on public.progress_photos(update_id);

alter table public.app_users enable row level security;
alter table public.tasks enable row level security;
alter table public.qcvn_items enable row level security;
alter table public.progress_updates enable row level security;
alter table public.progress_photos enable row level security;

grant all on public.app_users to service_role;
grant all on public.tasks to service_role;
grant all on public.qcvn_items to service_role;
grant all on public.progress_updates to service_role;
grant all on public.progress_photos to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'progress-photos',
    'progress-photos',
    false,
    12582912,
    array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
