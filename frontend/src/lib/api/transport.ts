export class ApiError extends Error {
  public status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  baseUrl: string | undefined,
  token: string | undefined,
  path: string,
  options: RequestInit = {},
  organizationId?: string,
  fetcher: typeof fetch = fetch,
): Promise<T> {
  if (!token) throw new ApiError(401, "로그인이 필요합니다.");
  if (!baseUrl) throw new ApiError(503, "API 연결 설정을 확인해 주세요.");
  if (!path.startsWith("/api/v1/") || path.includes("://")) throw new Error("Invalid API path");
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (options.body) headers.set("Content-Type", "application/json");
  if (organizationId) headers.set("X-Organization-Id", organizationId);
  let response: Response;
  try {
    response = await fetcher(baseUrl.replace(/\/$/, "") + path, {
      ...options, headers, cache: "no-store",
      signal: options.signal ?? AbortSignal.timeout(10000),
    });
  } catch {
    throw new ApiError(503, "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "로그인이 만료되었습니다. 다시 로그인해 주세요.",
      403: "이 사업장에 접근할 권한이 없습니다.",
      404: "숙소를 찾을 수 없습니다.",
      409: "이미 사업장 등록을 완료했습니다. 내 숙소로 이동해 주세요.",
      422: "입력 내용을 확인해 주세요.",
    };
    throw new ApiError(response.status, messages[response.status] ?? "요청을 처리할 수 없습니다.");
  }
  return response.json() as Promise<T>;
}
