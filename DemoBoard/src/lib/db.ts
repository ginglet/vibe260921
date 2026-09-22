import { promises as fs } from "node:fs";
import path from "node:path";
import { hashPassword, verifyPassword } from "./password";
import type {
  Category,
  Comment,
  Post,
  PostSummary,
  Store,
  StoredComment,
  StoredPost,
} from "./types";

/**
 * 데모용 JSON 파일 저장소.
 * 실서비스에서는 이 파일의 함수 시그니처를 유지한 채 DB(Prisma, Drizzle 등)로 교체하면 된다.
 */
const DATA_DIR = path.join(process.cwd(), "data");
const DATA_FILE = path.join(DATA_DIR, "posts.json");

export const PAGE_SIZE = 10;

// dev 서버의 HMR로 모듈이 여러 번 로드되어도 락이 하나만 존재하도록 globalThis에 둔다.
const globalForDb = globalThis as unknown as { __boardQueue?: Promise<unknown> };

function withLock<T>(fn: () => Promise<T>): Promise<T> {
  const prev = globalForDb.__boardQueue ?? Promise.resolve();
  const run = prev.then(fn, fn);
  globalForDb.__boardQueue = run.catch(() => undefined);
  return run;
}

function seed(): Store {
  const now = Date.now();
  const ago = (hours: number) => new Date(now - hours * 3_600_000).toISOString();
  const pw = hashPassword("1234");

  const posts: StoredPost[] = [
    {
      id: 1,
      title: "DemoBoard에 오신 것을 환영합니다",
      content:
        "Next.js, shadcn/ui, TypeScript로 만든 게시판 데모입니다.\n\n- 글 작성 / 수정 / 삭제\n- 댓글\n- 카테고리 필터와 검색\n- 페이지네이션\n\n글과 댓글은 작성 시 입력한 비밀번호로 수정·삭제할 수 있습니다. (샘플 글의 비밀번호는 1234)",
      author: "관리자",
      category: "공지",
      passwordHash: pw,
      views: 128,
      createdAt: ago(72),
      updatedAt: ago(72),
      comments: [],
    },
    {
      id: 2,
      title: "게시판 이용 안내",
      content:
        "서로를 존중하는 분위기에서 자유롭게 이야기해 주세요.\n비방, 광고, 개인정보가 담긴 글은 삭제될 수 있습니다.",
      author: "관리자",
      category: "공지",
      passwordHash: pw,
      views: 64,
      createdAt: ago(70),
      updatedAt: ago(70),
      comments: [],
    },
    {
      id: 3,
      title: "Next.js 16 써보신 분 계신가요?",
      content:
        "App Router로 새 프로젝트를 시작하려는데 params와 searchParams가 Promise로 바뀌었다고 하더군요.\n실제로 써보신 분들 후기가 궁금합니다.",
      author: "새싹개발자",
      category: "질문",
      passwordHash: pw,
      views: 42,
      createdAt: ago(30),
      updatedAt: ago(30),
      comments: [
        {
          id: 1,
          author: "고수",
          content: "await로 풀어서 쓰면 됩니다. PageProps 타입 헬퍼를 쓰면 편해요.",
          passwordHash: pw,
          createdAt: ago(28),
        },
        {
          id: 2,
          author: "새싹개발자",
          content: "감사합니다! 바로 적용해 볼게요.",
          passwordHash: pw,
          createdAt: ago(27),
        },
      ],
    },
    {
      id: 4,
      title: "shadcn/ui 컴포넌트로 게시판 만든 후기",
      content:
        "직접 스타일을 짜지 않아도 Table, Card, AlertDialog만으로 꽤 그럴듯한 게시판이 나오네요.\n다크 모드도 거의 공짜로 따라옵니다.",
      author: "디자이너K",
      category: "후기",
      passwordHash: pw,
      views: 87,
      createdAt: ago(12),
      updatedAt: ago(12),
      comments: [],
    },
    {
      id: 5,
      title: "점심 뭐 드셨어요?",
      content: "저는 김치찌개 먹었습니다. 여러분은요?",
      author: "배고픈사람",
      category: "자유",
      passwordHash: pw,
      views: 15,
      createdAt: ago(2),
      updatedAt: ago(2),
      comments: [],
    },
  ];

  return { nextPostId: 6, nextCommentId: 3, posts };
}

async function readStore(): Promise<Store> {
  try {
    const raw = await fs.readFile(DATA_FILE, "utf8");
    return JSON.parse(raw) as Store;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    const initial = seed();
    await writeStore(initial);
    return initial;
  }
}

async function writeStore(store: Store): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  const tmp = `${DATA_FILE}.${process.pid}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(store, null, 2), "utf8");
  await fs.rename(tmp, DATA_FILE);
}

function toComment({ passwordHash: _hash, ...comment }: StoredComment): Comment {
  return comment;
}

function toPost({ passwordHash: _hash, comments, ...post }: StoredPost): Post {
  return { ...post, comments: comments.map(toComment) };
}

function toSummary({ passwordHash: _hash, comments, content: _content, ...post }: StoredPost): PostSummary {
  return { ...post, commentCount: comments.length };
}

export interface ListParams {
  q?: string;
  category?: Category;
  page?: number;
}

export interface ListResult {
  items: PostSummary[];
  total: number;
  page: number;
  totalPages: number;
}

export async function listPosts({ q, category, page = 1 }: ListParams): Promise<ListResult> {
  const store = await readStore();
  const keyword = q?.trim().toLowerCase();

  const filtered = store.posts
    .filter((post) => !category || post.category === category)
    .filter(
      (post) =>
        !keyword ||
        post.title.toLowerCase().includes(keyword) ||
        post.content.toLowerCase().includes(keyword) ||
        post.author.toLowerCase().includes(keyword),
    )
    // 공지는 항상 위로, 나머지는 최신순
    .sort((a, b) => {
      const notice = Number(b.category === "공지") - Number(a.category === "공지");
      if (notice !== 0) return notice;
      return b.createdAt.localeCompare(a.createdAt);
    });

  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), totalPages);
  const start = (current - 1) * PAGE_SIZE;

  return {
    items: filtered.slice(start, start + PAGE_SIZE).map(toSummary),
    total,
    page: current,
    totalPages,
  };
}

/** 글 상세 조회. countView가 true면 조회수를 1 올린다. */
export function getPost(id: number, { countView = false } = {}): Promise<Post | null> {
  if (!countView) {
    return readStore().then((store) => {
      const post = store.posts.find((p) => p.id === id);
      return post ? toPost(post) : null;
    });
  }
  return withLock(async () => {
    const store = await readStore();
    const post = store.posts.find((p) => p.id === id);
    if (!post) return null;
    post.views += 1;
    await writeStore(store);
    return toPost(post);
  });
}

export type MutationError = "not_found" | "wrong_password";

export interface NewPost {
  title: string;
  content: string;
  author: string;
  category: Category;
  password: string;
}

export function createPost(input: NewPost): Promise<Post> {
  return withLock(async () => {
    const store = await readStore();
    const now = new Date().toISOString();
    const post: StoredPost = {
      id: store.nextPostId++,
      title: input.title,
      content: input.content,
      author: input.author,
      category: input.category,
      passwordHash: hashPassword(input.password),
      views: 0,
      createdAt: now,
      updatedAt: now,
      comments: [],
    };
    store.posts.push(post);
    await writeStore(store);
    return toPost(post);
  });
}

export function updatePost(
  id: number,
  input: NewPost,
): Promise<{ ok: true; post: Post } | { ok: false; error: MutationError }> {
  return withLock(async () => {
    const store = await readStore();
    const post = store.posts.find((p) => p.id === id);
    if (!post) return { ok: false, error: "not_found" };
    if (!verifyPassword(input.password, post.passwordHash)) return { ok: false, error: "wrong_password" };

    post.title = input.title;
    post.content = input.content;
    post.author = input.author;
    post.category = input.category;
    post.updatedAt = new Date().toISOString();
    await writeStore(store);
    return { ok: true, post: toPost(post) };
  });
}

export function deletePost(
  id: number,
  password: string,
): Promise<{ ok: true } | { ok: false; error: MutationError }> {
  return withLock(async () => {
    const store = await readStore();
    const index = store.posts.findIndex((p) => p.id === id);
    if (index === -1) return { ok: false, error: "not_found" };
    if (!verifyPassword(password, store.posts[index].passwordHash)) return { ok: false, error: "wrong_password" };

    store.posts.splice(index, 1);
    await writeStore(store);
    return { ok: true };
  });
}

export function addComment(
  postId: number,
  input: { author: string; content: string; password: string },
): Promise<{ ok: true } | { ok: false; error: "not_found" }> {
  return withLock(async () => {
    const store = await readStore();
    const post = store.posts.find((p) => p.id === postId);
    if (!post) return { ok: false, error: "not_found" };

    post.comments.push({
      id: store.nextCommentId++,
      author: input.author,
      content: input.content,
      passwordHash: hashPassword(input.password),
      createdAt: new Date().toISOString(),
    });
    await writeStore(store);
    return { ok: true };
  });
}

export function deleteComment(
  postId: number,
  commentId: number,
  password: string,
): Promise<{ ok: true } | { ok: false; error: MutationError }> {
  return withLock(async () => {
    const store = await readStore();
    const post = store.posts.find((p) => p.id === postId);
    const index = post?.comments.findIndex((c) => c.id === commentId) ?? -1;
    if (!post || index === -1) return { ok: false, error: "not_found" };
    if (!verifyPassword(password, post.comments[index].passwordHash)) return { ok: false, error: "wrong_password" };

    post.comments.splice(index, 1);
    await writeStore(store);
    return { ok: true };
  });
}
