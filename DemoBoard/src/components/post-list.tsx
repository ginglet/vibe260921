import Link from "next/link";
import { categoryBadgeColor } from "@/lib/category-colors";
import type { CategoryInfo, PostSummary } from "@/lib/types";

interface PostListProps {
  posts: PostSummary[];
  categories: CategoryInfo[];
}

export function PostList({ posts, categories }: PostListProps) {
  if (posts.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-card p-10 text-center text-muted-foreground">
        글이 없습니다.
      </div>
    );
  }

  const categoryByName = new Map(categories.map((c) => [c.name, c]));

  return (
    <div className="flex flex-col gap-2.5">
      {posts.map((post) => {
        const meta = categoryByName.get(post.category);
        const { bg, fg } = categoryBadgeColor(meta?.sortOrder ?? 0, meta?.isPinned ?? false);
        const isPinned = meta?.isPinned ?? false;

        return (
          <Link key={post.id} href={`/post/${post.id}`}>
            <div
              className="flex items-start gap-4 rounded-2xl border border-border bg-card p-[18px] transition-colors hover:border-primary/40"
              style={isPinned ? { borderLeft: "3px solid var(--primary)" } : undefined}
            >
              <span
                className="mt-0.5 shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold tracking-wide"
                style={{ backgroundColor: bg, color: fg }}
              >
                {post.category}
              </span>
              <div className="min-w-0 flex-1">
                <div className="mb-1.5 truncate text-[15px] font-semibold">{post.title}</div>
                <div className="flex flex-wrap items-center gap-x-3.5 gap-y-1 text-xs text-muted-foreground">
                  <span>{post.author}</span>
                  <span>{new Date(post.createdAt).toLocaleDateString("ko-KR")}</span>
                  <span>조회 {post.views}</span>
                  <span>댓글 {post.commentCount}</span>
                </div>
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
