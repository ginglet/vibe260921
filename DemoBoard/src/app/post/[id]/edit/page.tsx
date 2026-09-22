import { Suspense, use } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PostForm } from "@/components/post-form";
import { actionGetPost } from "@/app/actions";
import { listCategories } from "@/lib/db";

interface PageProps {
  params: Promise<{ id: string }>;
}

export const revalidate = 0;

async function EditContent({ id }: { id: number }) {
  const [result, categories] = await Promise.all([actionGetPost(id), listCategories()]);

  if (!result.ok) {
    return (
      <div className="rounded-lg bg-destructive/10 p-4 text-destructive">
        {result.error}
      </div>
    );
  }

  return <PostForm post={result.post} isEdit={true} categories={categories} />;
}

export default function EditPage({ params }: PageProps) {
  const { id } = use(params);
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
      <div>
        <Link href={`/post/${postId}`}>
          <Button variant="outline" size="sm">
            ← 돌아가기
          </Button>
        </Link>
      </div>

      <div>
        <h2 className="text-2xl font-bold">글 수정</h2>
      </div>

      <Suspense fallback={<div className="text-center text-muted-foreground py-12">로딩 중...</div>}>
        <EditContent id={postId} />
      </Suspense>
    </div>
  );
}
