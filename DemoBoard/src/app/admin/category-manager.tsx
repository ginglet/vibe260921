"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  actionAdminCreateCategory,
  actionAdminDeleteCategory,
  actionAdminRenameCategory,
  actionAdminSetCategoryPinned,
} from "./actions";
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
import type { CategoryInfo } from "@/lib/types";

export function CategoryManager({ categories }: { categories: CategoryInfo[] }) {
  const router = useRouter();
  const [newName, setNewName] = useState("");
  const [isPending, startTransition] = useTransition();

  const handleCreate = () => {
    if (!newName.trim()) return;
    startTransition(async () => {
      const result = await actionAdminCreateCategory(newName);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      toast.success("카테고리가 추가되었습니다.");
      setNewName("");
      router.refresh();
    });
  };

  return (
    <div className="space-y-3">
      {categories.length === 0 ? (
        <p className="text-sm text-muted-foreground">카테고리가 없습니다.</p>
      ) : (
        <div className="space-y-2">
          {categories.map((category) => (
            <CategoryRow key={category.id} category={category} />
          ))}
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <Input
          placeholder="새 카테고리 이름"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          disabled={isPending}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleCreate();
            }
          }}
        />
        <Button onClick={handleCreate} disabled={isPending || !newName.trim()}>
          {isPending ? "추가 중..." : "추가"}
        </Button>
      </div>
    </div>
  );
}

function CategoryRow({ category }: { category: CategoryInfo }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(category.name);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [isPending, startTransition] = useTransition();

  const handleRename = () => {
    const trimmed = name.trim();
    if (!trimmed || trimmed === category.name) {
      setEditing(false);
      setName(category.name);
      return;
    }
    startTransition(async () => {
      const result = await actionAdminRenameCategory(category.id, trimmed);
      if (!result.ok) {
        toast.error(result.error);
        setName(category.name);
        return;
      }
      toast.success("카테고리 이름이 변경되었습니다.");
      setEditing(false);
      router.refresh();
    });
  };

  const handleTogglePinned = (checked: boolean) => {
    startTransition(async () => {
      const result = await actionAdminSetCategoryPinned(category.id, checked);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      router.refresh();
    });
  };

  const handleDelete = () => {
    startTransition(async () => {
      const result = await actionAdminDeleteCategory(category.id);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      toast.success("카테고리가 삭제되었습니다.");
      setDeleteOpen(false);
      router.refresh();
    });
  };

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border p-2">
      {editing ? (
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isPending}
          autoFocus
          className="h-8"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleRename();
            }
            if (e.key === "Escape") {
              setEditing(false);
              setName(category.name);
            }
          }}
        />
      ) : (
        <span className="flex-1 text-sm font-medium">{category.name}</span>
      )}

      <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={category.isPinned}
          onChange={(e) => handleTogglePinned(e.target.checked)}
          disabled={isPending}
        />
        공지로 고정
      </label>

      {editing ? (
        <Button size="sm" variant="outline" onClick={handleRename} disabled={isPending}>
          저장
        </Button>
      ) : (
        <Button size="sm" variant="outline" onClick={() => setEditing(true)} disabled={isPending}>
          이름 변경
        </Button>
      )}

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogTrigger render={
          <Button size="sm" variant="destructive" disabled={isPending}>
            삭제
          </Button>
        } />
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>카테고리 삭제</AlertDialogTitle>
            <AlertDialogDescription>
              &quot;{category.name}&quot; 카테고리를 삭제하시겠습니까? 이 카테고리를 사용 중인 글이 있으면 삭제할 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isPending ? "삭제 중..." : "삭제"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
