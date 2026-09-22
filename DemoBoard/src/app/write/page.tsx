import { PostForm } from "@/components/post-form";
import { listCategories } from "@/lib/db";

export const metadata = {
  title: "새 글 작성 - DemoBoard",
};

export const revalidate = 0;

export default async function WritePage() {
  const categories = await listCategories();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">새 글 작성</h2>
      </div>
      <PostForm categories={categories} />
    </div>
  );
}
