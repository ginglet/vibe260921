import { Suspense } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PostList } from "@/components/post-list";
import { actionCountPostsByCategory, actionListCategories, actionListPosts } from "./actions";
import type { CategoryInfo } from "@/lib/types";

interface PageProps {
  searchParams: Promise<{
    q?: string;
    category?: string;
    page?: string;
    sort?: string;
  }>;
}

export const revalidate = 0; // 동적 렌더링

function buildQuery(params: Record<string, string | undefined>) {
  const entries = Object.entries(params).filter(([, v]) => v);
  return new URLSearchParams(entries as [string, string][]).toString();
}

async function PostListContainer({
  q,
  category,
  page,
  sort,
  categories,
}: {
  q?: string;
  category?: string;
  page: number;
  sort: "latest" | "popular";
  categories: CategoryInfo[];
}) {
  const result = await actionListPosts({
    q,
    category: category || undefined,
    page,
    sort,
  });

  if (!result.ok) {
    return <div className="rounded-2xl bg-destructive/10 p-4 text-destructive">{result.error}</div>;
  }

  const { items, total, totalPages } = result.result;

  return (
    <div className="space-y-6">
      <PostList posts={items} categories={categories} />

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <Link key={p} href={`/?${buildQuery({ q, category, sort, page: String(p) })}`}>
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-lg text-[13px] font-semibold transition-colors ${
                  p === page
                    ? "bg-primary text-primary-foreground"
                    : "border border-border text-muted-foreground hover:border-primary/40"
                }`}
              >
                {p}
              </span>
            </Link>
          ))}
        </div>
      )}
      {total === 0 && null}
    </div>
  );
}

export default async function Page({ searchParams }: PageProps) {
  const params = await searchParams;
  const q = params.q?.trim();
  const category = params.category?.trim();
  const page = Math.max(1, parseInt(params.page || "1"));
  const sort: "latest" | "popular" = params.sort === "popular" ? "popular" : "latest";

  const [categoriesResult, countsResult] = await Promise.all([
    actionListCategories(),
    actionCountPostsByCategory(),
  ]);
  const categories = categoriesResult.ok ? categoriesResult.categories : [];
  const counts = countsResult.ok ? countsResult.counts : {};
  const totalCount = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <div className="flex gap-8">
      {/* 사이드바 */}
      <aside className="flex w-60 shrink-0 flex-col gap-1.5 rounded-2xl border border-border bg-card p-4">
        <Link
          href={`/?${buildQuery({ q, sort })}`}
          className={`flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
            !category ? "bg-accent text-primary" : "text-muted-foreground hover:bg-muted"
          }`}
        >
          <span>전체글</span>
          <span className="text-xs opacity-70">{totalCount}</span>
        </Link>

        {categories.map((cat) => (
          <Link
            key={cat.id}
            href={`/?${buildQuery({ q, sort, category: cat.name })}`}
            className={`flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-colors ${
              category === cat.name
                ? "bg-accent font-semibold text-primary"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            <span>{cat.name}</span>
            <span className="text-xs opacity-70">{counts[cat.name] ?? 0}</span>
          </Link>
        ))}

        <div className="flex-1" />

        <Link href="/write">
          <Button className="mt-3 w-full">+ 새 글 작성</Button>
        </Link>
      </aside>

      {/* 본문 */}
      <div className="min-w-0 flex-1 space-y-5">
        <div className="flex items-center gap-3">
          <form action="/" method="get" className="flex flex-1 gap-2">
            {category && <input type="hidden" name="category" value={category} />}
            {sort !== "latest" && <input type="hidden" name="sort" value={sort} />}
            <Input
              name="q"
              placeholder="제목, 내용, 작성자로 검색..."
              defaultValue={q || ""}
              className="flex-1 rounded-xl"
            />
            <Button type="submit" variant="outline" className="rounded-xl">
              검색
            </Button>
          </form>

          <div className="flex gap-1 rounded-xl border border-border bg-card p-1">
            <Link href={`/?${buildQuery({ q, category })}`}>
              <span
                className={`inline-block rounded-lg px-4 py-1.5 text-[13px] font-semibold transition-colors ${
                  sort === "latest" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                최신순
              </span>
            </Link>
            <Link href={`/?${buildQuery({ q, category, sort: "popular" })}`}>
              <span
                className={`inline-block rounded-lg px-4 py-1.5 text-[13px] font-semibold transition-colors ${
                  sort === "popular" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                인기순
              </span>
            </Link>
          </div>
        </div>

        <Suspense fallback={<div className="rounded-2xl border border-border bg-card p-8 text-center">로딩 중...</div>}>
          <PostListContainer q={q} category={category} page={page} sort={sort} categories={categories} />
        </Suspense>
      </div>
    </div>
  );
}
