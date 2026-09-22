-- 카테고리를 동적으로 관리하기 위한 마이그레이션
-- Supabase SQL Editor에서 한 번 실행하세요.

-- 1) 카테고리 테이블 생성
create table if not exists public.categories (
  id bigint generated always as identity primary key,
  name text not null unique,
  sort_order integer not null default 0,
  is_pinned boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.categories enable row level security;

-- 2) 기존 4개 카테고리를 시드 데이터로 이관 (이미 있으면 건너뜀)
insert into public.categories (name, sort_order, is_pinned)
values
  ('공지', 0, true),
  ('자유', 1, false),
  ('질문', 2, false),
  ('후기', 3, false)
on conflict (name) do nothing;

-- 3) posts.category의 고정 CHECK 제약 제거 (더 이상 4개로 고정하지 않음)
alter table public.posts drop constraint if exists posts_category_check;

-- 4) is_notice를 generated column에서 일반 column으로 전환
--    (카테고리 이름이 바뀌어도 공지 여부를 카테고리별로 계속 추적하기 위함)
alter table public.posts drop column if exists is_notice;
alter table public.posts add column if not exists is_notice boolean not null default false;

update public.posts p
set is_notice = c.is_pinned
from public.categories c
where p.category = c.name;

-- 5) posts.category → categories.name 외래키
--    이름을 바꾸면 posts.category도 자동으로 따라가고(cascade),
--    사용 중인 카테고리는 삭제할 수 없도록(restrict) 막는다.
alter table public.posts drop constraint if exists posts_category_fkey;
alter table public.posts
  add constraint posts_category_fkey
  foreign key (category) references public.categories(name)
  on update cascade
  on delete restrict;

-- 6) 글이 추가/수정될 때 is_notice를 카테고리의 is_pinned 값으로 자동 동기화
create or replace function public.sync_post_is_notice()
returns trigger as $$
begin
  select is_pinned into new.is_notice from public.categories where name = new.category;
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_sync_post_is_notice on public.posts;
create trigger trg_sync_post_is_notice
before insert or update of category on public.posts
for each row execute function public.sync_post_is_notice();

-- 7) 관리자가 카테고리의 고정(공지) 여부를 바꾸면 해당 카테고리의 기존 글들도 함께 갱신
create or replace function public.sync_is_notice_on_category_change()
returns trigger as $$
begin
  if new.is_pinned is distinct from old.is_pinned then
    update public.posts set is_notice = new.is_pinned where category = new.name;
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_sync_is_notice_on_category_change on public.categories;
create trigger trg_sync_is_notice_on_category_change
after update of is_pinned on public.categories
for each row execute function public.sync_is_notice_on_category_change();

create index if not exists idx_categories_sort_order on public.categories(sort_order);
