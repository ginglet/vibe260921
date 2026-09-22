"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import { actionDeleteComment } from "@/app/actions";
import { actionAdminDeleteComment } from "@/app/admin/actions";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Comment } from "@/lib/types";

interface CommentListProps {
  postId: number;
  comments: Comment[];
  isAdmin?: boolean;
}

export function CommentList({ postId, comments, isAdmin = false }: CommentListProps) {
  if (comments.length === 0) {
    return <div className="rounded-lg bg-muted p-4 text-center text-sm text-muted-foreground">댓글이 없습니다.</div>;
  }

  return (
    <div className="space-y-3">
      {comments.map((comment) => (
        <CommentItem
          key={comment.id}
          postId={postId}
          comment={comment}
          isAdmin={isAdmin}
        />
      ))}
    </div>
  );
}

function CommentItem({
  postId,
  comment,
  isAdmin,
}: {
  postId: number;
  comment: Comment;
  isAdmin: boolean;
}) {
  const [showDelete, setShowDelete] = useState(false);
  const [password, setPassword] = useState("");
  const [isPending, startTransition] = useTransition();

  const action = async () => {
    const formData = new FormData();
    formData.set("password", password);
    const result = await actionDeleteComment(postId, comment.id, formData);
    if (!result.ok) {
      toast.error(result.error);
      setPassword("");
      return;
    }
    toast.success("댓글이 삭제되었습니다.");
    window.location.reload();
  };

  const adminAction = () => {
    startTransition(async () => {
      const result = await actionAdminDeleteComment(postId, comment.id);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      toast.success("댓글이 삭제되었습니다.");
      window.location.reload();
    });
  };

  const [isLoading, setIsLoading] = useState(false);

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-baseline gap-2">
              <span className="font-medium text-sm">{comment.author}</span>
              <span className="text-xs text-muted-foreground">
                {new Date(comment.createdAt).toLocaleString("ko-KR")}
              </span>
            </div>
            <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">{comment.content}</p>
          </div>
          <AlertDialog open={showDelete} onOpenChange={setShowDelete}>
            <AlertDialogTrigger render={
              <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                삭제
              </Button>
            } />
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>댓글 삭제</AlertDialogTitle>
                <AlertDialogDescription>
                  {isAdmin
                    ? "관리자 권한으로 이 댓글을 삭제합니다."
                    : "댓글을 삭제하시려면 작성 시 입력한 비밀번호를 입력하세요."}
                </AlertDialogDescription>
              </AlertDialogHeader>
              {!isAdmin && (
                <div>
                  <Label htmlFor="delete-password">비밀번호</Label>
                  <Input
                    id="delete-password"
                    type="password"
                    placeholder="비밀번호"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                  />
                </div>
              )}
              <AlertDialogFooter>
                <AlertDialogCancel>취소</AlertDialogCancel>
                {isAdmin ? (
                  <Button
                    onClick={adminAction}
                    disabled={isPending}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    {isPending ? "삭제 중..." : "삭제"}
                  </Button>
                ) : (
                <Button
                  onClick={async () => {
                    setIsLoading(true);
                    try {
                      await action();
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                  disabled={isLoading || !password}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {isLoading ? "삭제 중..." : "삭제"}
                </Button>
                )}
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
