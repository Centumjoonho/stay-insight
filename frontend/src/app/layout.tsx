import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stay Insight",
  description: "숙박업 운영 관리를 위한 Stay Insight 개발 환경",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <header className="border-b border-slate-200 bg-white px-6 py-5">
          <nav aria-label="주 메뉴" className="mx-auto flex max-w-3xl items-center justify-between">
            <Link href="/" className="text-lg font-semibold">Stay Insight</Link>
            <Link href="/health" className="text-sm underline underline-offset-4">연결 상태</Link>
          </nav>
        </header>
        <main className="mx-auto max-w-3xl px-6 py-16">{children}</main>
      </body>
    </html>
  );
}
