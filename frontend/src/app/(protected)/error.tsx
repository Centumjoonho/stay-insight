"use client";
import Link from "next/link";
export default function ProtectedError({ reset }: { reset: () => void }) {
  return <section role="alert"><h1>요청을 처리하지 못했습니다.</h1>
    <p className="mt-3">서버 연결과 접근 권한을 확인해 주세요.</p>
    <button className="action mt-4" onClick={reset}>다시 시도</button>
    <Link href="/login" className="ml-4 underline">로그인</Link></section>;
}
