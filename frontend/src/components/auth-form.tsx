"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { browserAuth } from "@/lib/supabase/client";
import { authConfiguration } from "@/lib/supabase/config";
import { signupRedirectOptions } from "@/lib/supabase/redirects";
import { businessApi } from "@/lib/api/client";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const configured = Boolean(authConfiguration());
  const title = mode === "login" ? "로그인" : "회원가입";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    const credentials = { email: String(form.get("email")), password: String(form.get("password")) };
    try {
      const auth = browserAuth();
      const result = mode === "login"
        ? await auth.auth.signInWithPassword(credentials)
        : await auth.auth.signUp({
          ...credentials, options: signupRedirectOptions(),
        });
      if (result.error) {
        setMessage(mode === "login" ? "이메일과 비밀번호를 확인해 주세요." : "가입 정보를 확인하거나 잠시 후 다시 시도해 주세요.");
        return;
      }
      if (!result.data.session) {
        setMessage("이메일을 확인하여 가입을 완료한 후 로그인해 주세요.");
        return;
      }
      const me = await businessApi.me();
      router.replace(me.memberships.length ? "/properties" : "/onboarding");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "인증 요청을 처리할 수 없습니다.");
    } finally {
      setBusy(false);
    }
  }
  return <section>
    <h1 className="text-2xl font-semibold">{title}</h1>
    {!configured && <p role="alert" className="mt-4">Supabase 인증 설정이 필요합니다. 관리자에게 문의해 주세요.</p>}
    <form onSubmit={submit} className="mt-6 grid max-w-md gap-4">
      <label>이메일<input name="email" type="email" autoComplete="email" required className="field" /></label>
      <label>비밀번호<input name="password" type="password" minLength={mode === "signup" ? 8 : undefined} autoComplete={mode === "login" ? "current-password" : "new-password"} required className="field" /></label>
      <button disabled={busy || !configured} className="action">{busy ? "처리 중…" : title}</button>
      <p role="status">{message}</p>
    </form>
    <Link href={mode === "login" ? "/signup" : "/login"} className="mt-4 inline-block underline">
      {mode === "login" ? "회원가입" : "로그인으로 돌아가기"}
    </Link>
  </section>;
}
