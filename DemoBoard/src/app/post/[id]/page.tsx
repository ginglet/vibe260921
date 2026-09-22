import { Suspense, use } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CommentList } from "@/components/comment-list";
import { CommentForm } from "@/components/comment-form";
import { PostActions } from "./post-actions";
import { actionGetPost } from "@/app/actions";

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ readonly [key: string]: string | string[] | undefined }>;
}

export const revalidate = 0;

async function PostDetail({ id }: { id: number }) {
  const result = await actionGetPost(id);

  if (!result.ok) {
    return (
      <div className="rounded-lg bg-destructive/10 p-4 text-destructive">
        {result.error}
      </div>
    );
  }

  const post = result.post;
  const CATEGORY_COLORS: Record<string, "default" | "secondary" | "destructive"> = {
    공지: "destructive",
    자유: "default",
    질문: "secondary",
    후기: "default",
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={CATEGORY_COLORS[post.category] || "default"}>
                  {post.category}
                </Badge>
              </div>
              <h1 className="text-3xl font-bold">{post.title}</h1>
            </div>
            <PostActions postId={post.id} />
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="pt-6">
          <div className="mb-6 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <div>
              <span className="font-medium">{post.author}</span>
            </div>
            <div>
              {new Date(post.createdAt).toLocaleString("ko-KR")}
            </div>
            {post.updatedAt !== post.createdAt && (
              <div>
                수정: {new Date(post.updatedAt).toLocaleString("ko-KR")}
              </div>
            )}
            <div>조회 {post.views}</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-foreground leading-relaxed">
            {post.content}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold mb-4">댓글 ({post.comments.length})</h2>
          <Suspense fallback={<div className="text-center text-muted-foreground">로딩 중...</div>}>
            <CommentList postId={post.id} comments={post.comments} />
          </Suspense>
        </div>

        <CommentForm postId={post.id} />
      </div>
    </div>
  );
}

export default function Page({ params, searchParams }: PageProps) {
  const { id } = use(params);
  use(searchParams); // 타입 체크용
  const postId = parseInt(id, 10);

  if (Number.isNaN(postId)) {
    return (
      <div className="rounded-lg bg-destructive/10 p-4 text-destructive">
        잘못된 글 번호입니다.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link href="/">
        <Button variant="outline" size="sm">
          ← 돌아가기
        </Button>
      </Link>

      <Suspense fallback={<div className="text-center text-muted-foreground py-12">로딩 중...</div>}>
        <PostDetail id={postId} />
      </Suspense>
    </div>
  );
}
