import { NextResponse, type NextRequest } from "next/server";
import { serverAuth } from "@/lib/supabase/server";
import { publicAuthUrl } from "@/lib/supabase/redirects";

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const auth = await serverAuth();
  let destination: "/login" | "/onboarding" = "/login";
  if (code && auth) {
    const { error } = await auth.auth.exchangeCodeForSession(code);
    if (!error) destination = "/onboarding";
  }
  const response = NextResponse.redirect(publicAuthUrl(destination));
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}
