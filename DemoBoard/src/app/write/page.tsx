import { PostForm } from "@/components/post-form";

export const metadata = {
  title: "새 글 작성 - DemoBoard",
};

export default function WritePage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">새 글 작성</h2>
      </div>
      <PostForm />
    </div>
  );
}
