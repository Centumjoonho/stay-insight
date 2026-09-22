import { NextResponse, type NextRequest } from "next/server";
import { serverAuth } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const auth = await serverAuth();
  if (code && auth) {
    const { error } = await auth.auth.exchangeCodeForSession(code);
    if (!error) {
      const response = NextResponse.redirect(new URL("/onboarding", request.url));
      response.headers.set("Cache-Control", "private, no-store");
      return response;
    }
  }
  return NextResponse.redirect(new URL("/login", request.url));
}
