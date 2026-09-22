import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { authConfiguration } from "@/lib/supabase/config";
import { publicAuthUrl } from "@/lib/supabase/redirects";

export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });
  response.headers.set("Cache-Control", "private, no-store");
  const protectedPath = request.nextUrl.pathname.startsWith("/properties") ||
    request.nextUrl.pathname === "/onboarding";
  const config = authConfiguration();
  const redirectToLogin = () => {
    const redirect = NextResponse.redirect(publicAuthUrl("/login"));
    response.cookies.getAll().forEach((cookie) => redirect.cookies.set(cookie));
    redirect.headers.set("Cache-Control", "private, no-store");
    return redirect;
  };
  if (!config) return protectedPath ? redirectToLogin() : response;
  const auth = createServerClient(config.url, config.key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (values) => {
        values.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        values.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        response.headers.set("Cache-Control", "private, no-store");
      },
    },
  });
  const { data, error } = await auth.auth.getClaims();
  if (protectedPath && (error || !data?.claims)) return redirectToLogin();
  return response;
}

export const config = {
  matcher: ["/login", "/signup", "/onboarding", "/properties/:path*", "/auth/callback"],
};
