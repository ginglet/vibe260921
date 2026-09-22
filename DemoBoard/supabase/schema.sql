-- Enable extensions
create extension if not exists pg_trgm;

-- Enable RLS (policies will be managed by server only)
alter table public.posts enable row level security;
alter table public.comments enable row level security;

-- Posts table
create table if not exists public.posts (
  id bigint generated always as identity primary key,
  title text not null,
  content text not null,
  author text not null,
  category text not null check (category in ('공지', '자유', '질문', '후기')),
  password_hash text not null,
  views integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  is_notice boolean generated always as (category = '공지') stored
);

-- Comments table with cascade delete
create table if not exists public.comments (
  id bigint generated always as identity primary key,
  post_id bigint not null references public.posts(id) on delete cascade,
  author text not null,
  content text not null,
  password_hash text not null,
  created_at timestamptz not null default now()
);

-- Indexes for performance
create index if not exists idx_posts_category on public.posts(category);
create index if not exists idx_posts_created_at on public.posts(created_at desc);
create index if not exists idx_posts_is_notice_created_at on public.posts(is_notice, created_at desc);
create index if not exists idx_comments_post_id on public.comments(post_id);
create index if not exists idx_comments_created_at on public.comments(created_at);

-- Full-text search indexes (GIN for ILIKE queries)
create index if not exists idx_posts_title_trgm on public.posts using gin (title gin_trgm_ops);
create index if not exists idx_posts_content_trgm on public.posts using gin (content gin_trgm_ops);
create index if not exists idx_posts_author_trgm on public.posts using gin (author gin_trgm_ops);

-- Function to atomically increment post views
create or replace function public.increment_post_views(post_id bigint)
returns void as $$
begin
  update public.posts
  set views = views + 1
  where id = post_id;
end;
$$ language plpgsql;

-- Seed data (password for all samples: 1234, hashed)
insert into public.posts (title, content, author, category, password_hash, views, created_at, updated_at)
values
  (
    'DemoBoard에 오신 것을 환영합니다',
    'Next.js, shadcn/ui, TypeScript로 만든 게시판 데모입니다.

- 글 작성 / 수정 / 삭제
- 댓글
- 카테고리 필터와 검색
- 페이지네이션

글과 댓글은 작성 시 입력한 비밀번호로 수정·삭제할 수 있습니다. (샘플 글의 비밀번호는 1234)',
    '관리자',
    '공지',
    '8b5f9e8e3d8e3d8e3d8e3d8e3d8e3d8e:6430157a66dbea6a02ddd9f41f6e0f26ed1f7558727f8c24a0119bda19c06dc5',
    128,
    now() - interval '72 hours',
    now() - interval '72 hours'
  ),
  (
    '게시판 이용 안내',
    '서로를 존중하는 분위기에서 자유롭게 이야기해 주세요.
비방, 광고, 개인정보가 담긴 글은 삭제될 수 있습니다.',
    '관리자',
    '공지',
    '8b5f9e8e3d8e3d8e3d8e3d8e3d8e3d8e:6430157a66dbea6a02ddd9f41f6e0f26ed1f7558727f8c24a0119bda19c06dc5',
    64,
    now() - interval '70 hours',
    now() - interval '70 hours'
  ),
  (
    'Next.js 16 써보신 분 계신가요?',
    'App Router로 새 프로젝트를 시작하려는데 params와 searchParams가 Promise로 바뀌었다고 하더군요.
실제로 써보신 분들 후기가 궁금합니다.',
    '새싹개발자',
    '질문',
    '8b5f9e8e3d8e3d8e3d8e3d8e3d8e3d8e:6430157a66dbea6a02ddd9f41f6e0f26ed1f7558727f8c24a0119bda19c06dc5',
    42,
    now() - interval '30 hours',
    now() - interval '30 hours'
  ),
  (
    'shadcn/ui 컴포넌트로 게시판 만든 후기',
    '직접 스타일을 짜지 않아도 Table, Card, AlertDialog만으로 꽤 그럴듯한 게시판이 나오네요.
다크 모드도 거의 공짜로 따라옵니다.',
    '디자이너K',
    '후기',
    '8b5f9e8e3d8e3d8e3d8e3d8e3d8e3d8e:6430157a66dbea6a02ddd9f41f6e0f26ed1f7558727f8c24a0119bda19c06dc5',
    87,
    now() - interval '12 hours',
    now() - interval '12 hours'
  ),
  (
    '점심 뭐 드셨어요?',
    '저는 김치찌개 먹었습니다. 여러분은요?',
    '배고픈사람',
    '자유',
    '8b5f9e8e3d8e3d8e3d8e3d8e3d8e3d8e:6430157a66dbea6a02ddd9f41f6e0f26ed1f7558727f8c24a0119bda19c06dc5',
    15,
    now() - interval '2 hours',
    now() - interval '2 hours'
  )
on conflict do nothing;

-- Seed comments
insert into public.comments (post_id, author, content, password_hash, created_at)
values
  (
    3,
    '고수',
    'await로 풀어서 쓰면 됩니다. PageProps 타입 헬퍼를 쓰면 편해요.',
    '8b5f9e8e3d8e3d8e3d8e3d8e3d8e3d8e:6430157a66dbea6a02ddd9f41f6e0f26ed1f7558727f8c24a0119bda19c06dc5',
    now() - interval '28 hours'
  ),
  (
    3,
    '새싹개발자',
    '감사합니다! 바로 적용해 볼게요.',
    '8b5f9e8e3d8e3d8e3d8e3d8e3d8e3d8e:6430157a66dbea6a02ddd9f41f6e0f26ed1f7558727f8c24a0119bda19c06dc5',
    now() - interval '27 hours'
  )
on conflict do nothing;
