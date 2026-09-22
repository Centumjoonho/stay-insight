import Link from "next/link";

export default function HomePage() {
  return (
    <section>
      <p className="mb-3 text-sm font-medium text-slate-500">Stay Insight · 사업장 관리</p>
      <h1 className="text-3xl font-semibold tracking-tight">Stay Insight</h1>
      <p className="mt-5 leading-7 text-slate-600">숙박업 운영 관리를 위한 프로젝트의 기본 환경입니다.</p>
      <Link href="/properties" className="mt-8 inline-block rounded-lg bg-slate-900 px-5 py-3 text-white">
        내 숙소로 이동
      </Link>
    </section>
  );
}
