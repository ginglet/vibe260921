"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { PostSummary } from "@/lib/types";

interface PostListProps {
  posts: PostSummary[];
}

const CATEGORY_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  공지: "destructive",
  자유: "default",
  질문: "secondary",
  후기: "default",
};

export function PostList({ posts }: PostListProps) {
  if (posts.length === 0) {
    return <div className="rounded-lg bg-muted p-8 text-center text-muted-foreground">글이 없습니다.</div>;
  }

  return (
    <div className="space-y-2">
      {posts.map((post) => (
        <Link key={post.id} href={`/post/${post.id}`}>
          <Card className="p-4 transition-colors hover:bg-muted/50">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={CATEGORY_COLORS[post.category] || "default"} className="text-xs">
                    {post.category}
                  </Badge>
                  {post.commentCount > 0 && (
                    <span className="text-xs text-destructive font-bold">[{post.commentCount}]</span>
                  )}
                </div>
                <h3 className="font-medium truncate hover:text-primary">{post.title}</h3>
                <div className="mt-2 text-xs text-muted-foreground space-y-1">
                  <div>
                    작성자: <span className="font-medium">{post.author}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>{new Date(post.createdAt).toLocaleDateString("ko-KR")}</span>
                    <span>조회 {post.views}</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
