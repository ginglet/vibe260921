import { Suspense, use } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PostList } from "@/components/post-list";
import { actionListPosts } from "./actions";
import { CATEGORIES } from "@/lib/types";

interface PageProps {
  searchParams: Promise<{
    q?: string;
    category?: string;
    page?: string;
  }>;
}

export const revalidate = 0; // 동적 렌더링

async function PostListContainer({ q, category, page }: { q?: string; category?: string; page: number }) {
  const result = await actionListPosts({
    q,
    category: category && CATEGORIES.includes(category as any) ? (category as any) : undefined,
    page,
  });

  if (!result.ok) {
    return <div className="rounded-lg bg-destructive/10 p-4 text-destructive">{result.error}</div>;
  }

  const { items, total, totalPages } = result.result;

  return (
    <div className="space-y-6">
      <PostList posts={items} />

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <Link
              key={p}
              href={`/?${new URLSearchParams({
                ...(q && { q }),
                ...(category && { category }),
                page: String(p),
              })}`}
            >
              <Button
                variant={p === page ? "default" : "outline"}
                size="sm"
              >
                {p}
              </Button>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Page({ searchParams }: PageProps) {
  const params = use(searchParams);
  const q = params.q?.trim();
  const category = params.category?.trim();
  const page = Math.max(1, parseInt(params.page || "1"));

  return (
    <div className="space-y-6">
      {/* 검색 및 필터 */}
      <div className="space-y-4">
        <form action="/" method="get" className="flex gap-2">
          <Input
            name="q"
            placeholder="제목, 내용, 작성자로 검색..."
            defaultValue={q || ""}
            className="flex-1"
          />
          <Button type="submit" variant="outline">
            검색
          </Button>
        </form>

        <div className="flex flex-wrap gap-2">
          <Link href="/">
            <Button
              variant={!category ? "default" : "outline"}
              size="sm"
            >
              전체
            </Button>
          </Link>
          {CATEGORIES.map((cat) => (
            <Link
              key={cat}
              href={`/?${new URLSearchParams({ category: cat, ...(q && { q }) })}`}
            >
              <Button
                variant={category === cat ? "default" : "outline"}
                size="sm"
              >
                {cat}
              </Button>
            </Link>
          ))}
        </div>
      </div>

      {/* 글 작성 버튼 */}
      <div className="flex justify-end">
        <Link href="/write">
          <Button>새 글 작성</Button>
        </Link>
      </div>

      {/* 글 목록 */}
      <Suspense fallback={<div className="rounded-lg bg-muted p-8 text-center">로딩 중...</div>}>
        <PostListContainer q={q} category={category} page={page} />
      </Suspense>
    </div>
  );
}
