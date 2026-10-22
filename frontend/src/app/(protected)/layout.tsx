export const dynamic = "force-dynamic";
import { requireToken } from "@/lib/api/server";

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  await requireToken();
  return <>{children}</>;
}
