import { AdminLoginForm } from "./login-form";

export const revalidate = 0;

export default function AdminLoginPage() {
  return (
    <div className="mx-auto max-w-sm space-y-6">
      <h2 className="text-center text-2xl font-bold">관리자 로그인</h2>
      <AdminLoginForm />
    </div>
  );
}
