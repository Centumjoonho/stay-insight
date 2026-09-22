type AuthPath = "/auth/callback" | "/login" | "/onboarding";

/** Public origin is explicit: never infer it from Docker or request headers. */
export function publicAuthUrl(path: AuthPath): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (!configured) throw new Error("NEXT_PUBLIC_SITE_URL 설정이 필요합니다.");
  let site: URL;
  try {
    site = new URL(configured);
  } catch {
    throw new Error("NEXT_PUBLIC_SITE_URL은 유효한 공개 HTTP(S) 주소여야 합니다.");
  }
  if (!["http:", "https:"].includes(site.protocol) ||
      ["0.0.0.0", "[::]"].includes(site.hostname) ||
      site.username || site.password || site.pathname !== "/" || site.search || site.hash) {
    throw new Error("NEXT_PUBLIC_SITE_URL은 바인딩 주소가 아닌 공개 HTTP(S) origin이어야 합니다.");
  }
  return new URL(path, site.origin).href;
}

export function signupRedirectOptions() {
  return { emailRedirectTo: publicAuthUrl("/auth/callback") };
}
