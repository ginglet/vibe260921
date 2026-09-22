import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DemoBoard",
  description: "Next.js 16, shadcn/ui, TypeScript로 만든 게시판",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <header className="border-b border-border bg-card/50 backdrop-blur supports-backdrop-filter:bg-card/30">
          <div className="mx-auto max-w-3xl px-4 py-4">
            <h1 className="text-2xl font-bold">
              <a href="/" className="hover:text-primary transition-colors">
                DemoBoard
              </a>
            </h1>
          </div>
        </header>
        <main className="flex-1 mx-auto w-full max-w-3xl px-4 py-8">
          {children}
        </main>
        <Toaster />
      </body>
    </html>
  );
}
