import { redirect } from "next/navigation";
import { serverApi } from "@/lib/api/server";
import { OnboardingForm } from "@/components/onboarding-form";

export default async function OnboardingPage() {
  const me = await serverApi.me();
  if (me.memberships.length) redirect("/properties");
  return <section><h1 className="text-2xl font-semibold">사업장 등록</h1><OnboardingForm /></section>;
}
