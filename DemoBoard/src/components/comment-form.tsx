"use client";

import { useActionState, useState } from "react";
import { toast } from "sonner";
import { actionAddComment } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";

interface CommentFormProps {
  postId: number;
  onSuccess?: () => void;
}

export function CommentForm({ postId, onSuccess }: CommentFormProps) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isPending, setIsPending] = useState(false);

  const handleSubmit = async (formData: FormData) => {
    setIsPending(true);
    try {
      const result = await actionAddComment(postId, formData);
      if (!result.ok) {
        setErrors(result.values ? {} : { form: result.error });
        if (result.error) toast.error(result.error);
        return;
      }
      toast.success("댓글이 작성되었습니다.");
      onSuccess?.();
    } finally {
      setIsPending(false);
    }
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <form action={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="comment-author">작성자</Label>
              <Input
                id="comment-author"
                name="author"
                placeholder="이름"
                disabled={isPending}
                required
              />
            </div>
            <div>
              <Label htmlFor="comment-password">비밀번호</Label>
              <Input
                id="comment-password"
                name="password"
                type="password"
                placeholder="4~50자"
                disabled={isPending}
                required
              />
            </div>
          </div>

          <div>
            <Label htmlFor="comment-content">댓글 내용</Label>
            <Textarea
              id="comment-content"
              name="content"
              placeholder="댓글을 입력하세요"
              rows={3}
              disabled={isPending}
              required
            />
          </div>

          {errors.form && <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{errors.form}</div>}

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? "작성 중..." : "댓글 작성"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
