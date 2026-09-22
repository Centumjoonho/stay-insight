export async function checkBackendHealth(
  baseUrl: string | undefined,
  signal: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<boolean> {
  if (!baseUrl) return false;

  try {
    const url = new URL(`${baseUrl.replace(/\/$/, "")}/api/v1/health`);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;

    const response = await fetcher(url, { signal, cache: "no-store" });
    if (!response.ok) return false;
    const body: unknown = await response.json();
    return typeof body === "object" && body !== null && "status" in body && body.status === "ok";
  } catch {
    return false;
  }
}
