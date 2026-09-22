import { createBrowserClient } from "@supabase/ssr";
import { authConfiguration } from "./config";

export function browserAuth() {
  const config = authConfiguration();
  if (!config) throw new Error("Supabase 인증 설정이 필요합니다.");
  return createBrowserClient(config.url, config.key);
}
