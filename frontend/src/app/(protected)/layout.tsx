export const dynamic = "force-dynamic";
import Link from "next/link";
import { requireToken } from "@/lib/api/server";
import { SignOut } from "@/components/sign-out";

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  await requireToken();
  return <><nav aria-label="사업장 메뉴" className="mb-8 flex justify-between">
    <Link href="/properties" className="underline">내 숙소</Link><SignOut />
  </nav>{children}</>;
}
