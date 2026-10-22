import type { Metadata } from "next";
import { AppHeader } from "@/components/app-header";
import "@fontsource-variable/noto-sans-kr";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stay Insight",
  description: "숙박업 운영 관리를 위한 Stay Insight 개발 환경",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <AppHeader />
        <main id="main-content" className="app-container">{children}</main>
      </body>
    </html>
  );
}
