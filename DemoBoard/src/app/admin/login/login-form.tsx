"use client";

import { useActionState } from "react";
import { actionAdminLogin } from "../actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function AdminLoginForm() {
  const [state, formAction, isPending] = useActionState(actionAdminLogin, undefined);

  return (
    <Card>
      <CardContent className="pt-6">
        <form action={formAction} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="admin-password">관리자 비밀번호</Label>
            <Input
              id="admin-password"
              name="password"
              type="password"
              placeholder="비밀번호"
              autoFocus
              disabled={isPending}
            />
          </div>
          {state?.error && <p className="text-sm text-destructive">{state.error}</p>}
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? "로그인 중..." : "로그인"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
