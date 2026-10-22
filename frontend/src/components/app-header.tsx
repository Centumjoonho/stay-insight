"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOut } from "./sign-out";

export function AppHeader() {
  const path = usePathname();
  const protectedPage = path.startsWith("/properties") || path.startsWith("/onboarding");
  return <header className="app-header"><a href="#main-content" className="skip-link">본문으로 이동</a><nav className="header-inner" aria-label="주 메뉴">
    <Link className="brand" href="/">Stay Insight</Link>
    {protectedPage && <Link className="global-current" aria-current={path.startsWith("/properties") ? "page" : undefined} href="/properties">내 숙소</Link>}
    <div className="header-actions"><Link href="/health" aria-current={path === "/health" ? "page" : undefined}>연결 상태</Link>{protectedPage && <SignOut />}</div>
  </nav></header>;
}
