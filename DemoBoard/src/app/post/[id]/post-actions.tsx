"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { actionDeletePost } from "@/app/actions";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface PostActionsProps {
  postId: number;
}

export function PostActions({ postId }: PostActionsProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleDelete = async () => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.set("password", password);
      const result = await actionDeletePost(postId, formData);
      if (!result.ok) {
        toast.error(result.error);
        setPassword("");
        return;
      }
      toast.success("글이 삭제되었습니다.");
      setOpen(false);
      router.push("/");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex gap-2">
      <Link href={`/post/${postId}/edit`}>
        <Button variant="outline" size="sm">
          수정
        </Button>
      </Link>

      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogTrigger render={
          <Button variant="destructive" size="sm">
            삭제
          </Button>
        } />
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>글 삭제</AlertDialogTitle>
            <AlertDialogDescription>
              글을 삭제하시려면 작성 시 입력한 비밀번호를 입력하세요.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div>
            <Label htmlFor="post-delete-password">비밀번호</Label>
            <Input
              id="post-delete-password"
              type="password"
              placeholder="비밀번호"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isLoading || !password}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isLoading ? "삭제 중..." : "삭제"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
