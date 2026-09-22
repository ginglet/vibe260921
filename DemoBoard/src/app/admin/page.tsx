import { redirect } from "next/navigation";
import { isAdmin } from "@/lib/admin";
import { listCategories, listPosts } from "@/lib/db";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AdminPostRow } from "./admin-post-row";
import { CategoryManager } from "./category-manager";
import { actionAdminLogout } from "./actions";

export const revalidate = 0;

export default async function AdminPage() {
  if (!(await isAdmin())) {
    redirect("/admin/login");
  }

  const [{ items, total }, categories] = await Promise.all([
    listPosts({ page: 1, pageSize: 200 }),
    listCategories(),
  ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">관리자 대시보드</h2>
        <form action={actionAdminLogout}>
          <Button type="submit" variant="outline" size="sm">
            로그아웃
          </Button>
        </form>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>카테고리 관리</CardTitle>
        </CardHeader>
        <CardContent>
          <CategoryManager categories={categories} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>전체 글 ({total})</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <p className="text-sm text-muted-foreground">글이 없습니다.</p>
          ) : (
            <div>
              {items.map((post) => (
                <AdminPostRow key={post.id} post={post} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
