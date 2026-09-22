"use client";

import { useActionState, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  actionCreatePost,
  actionUpdatePost,
} from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CATEGORIES } from "@/lib/types";
import type { Post } from "@/lib/types";

interface PostFormProps {
  post?: Post;
  isEdit?: boolean;
}

export function PostForm({ post, isEdit }: PostFormProps) {
  const router = useRouter();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isPending, setIsPending] = useState(false);

  const handleSubmit = async (formData: FormData) => {
    setIsPending(true);
    try {
      if (isEdit && post) {
        const result = await actionUpdatePost(post.id, formData);
        if (!result.ok) {
          setErrors(result.values ? {} : { form: result.error });
          if (result.error) toast.error(result.error);
          return;
        }
        toast.success("글이 수정되었습니다.");
        router.push(`/post/${post.id}`);
      } else {
        const result = await actionCreatePost(formData);
        if (!result.ok) {
          setErrors(result.values ? {} : { form: result.error });
          if (result.error) toast.error(result.error);
          return;
        }
        toast.success("글이 작성되었습니다.");
        router.push(`/post/${result.postId}`);
      }
    } finally {
      setIsPending(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? "글 수정" : "새 글 작성"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form action={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="category">카테고리</Label>
            <select
              id="category"
              name="category"
              defaultValue={post?.category || ""}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-1"
              required
            >
              <option value="">선택하세요</option>
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="title">제목</Label>
            <Input
              id="title"
              name="title"
              placeholder="제목을 입력하세요"
              defaultValue={post?.title || ""}
              disabled={isPending}
              required
            />
          </div>

          <div>
            <Label htmlFor="author">작성자</Label>
            <Input
              id="author"
              name="author"
              placeholder="작성자 이름을 입력하세요"
              defaultValue={post?.author || ""}
              disabled={isPending}
              required
            />
          </div>

          <div>
            <Label htmlFor="content">내용</Label>
            <Textarea
              id="content"
              name="content"
              placeholder="내용을 입력하세요"
              defaultValue={post?.content || ""}
              rows={12}
              disabled={isPending}
              required
            />
          </div>

          <div>
            <Label htmlFor="password">비밀번호</Label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="글 수정/삭제 시 필요합니다"
              disabled={isPending}
              required
            />
          </div>

          {errors.form && <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{errors.form}</div>}

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? "처리 중..." : isEdit ? "수정하기" : "작성하기"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
