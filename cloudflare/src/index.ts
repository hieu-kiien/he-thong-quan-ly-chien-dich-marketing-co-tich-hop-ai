/**
 * Worker nay KHONG con chay backend trong Cloudflare Containers.
 *
 * Ly do: tai khoan nay khong co Workers Paid plan, Cloudflare tra
 * "Unauthorized: You do not have access to Cloudflare Containers. Deploying
 * containers requires the Workers Paid plan" — nen binding container khong bao
 * gio chay duoc va moi route /api/* tra 404.
 *
 * Kien truc moi: Worker chi lam HAI viec —
 *   1. phuc vu frontend tinh (ASSETS binding);
 *   2. proxy /api/* va /health sang backend that o BACKEND_ORIGIN.
 * Backend FastAPI chay o Render (xem render.yaml). Toan bo quyen ghi du lieu
 * bay gio thuoc backend do, nen khong con can co Durable Object snapshot R2
 * nua — SQLite cua backend nam tren dia chi persistent cua Render.
 */

interface Env {
  ASSETS: Fetcher;
  /** URL goc cua backend FastAPI, vd https://marketflow-api.onrender.com */
  BACKEND_ORIGIN: string;
  /** Xac thuc cho cron goi POST /api/v1/schedules/trigger-worker. */
  SCHEDULER_SECRET: string;
}

/**
 * Cron 5 phut/lan: scheduler o backend Render chay trong container nen bi
 * tu tat. Worker danh thuc no bang cach goi endpoint trigger, truyen secret
 * de chung minh la tin duoc.
 */
const SCHEDULER_CRON_EXPRESSION = "*/5 * * * *";

/** Headers can forward nguyen ven; phan con lai cua request khong can. */
const FORWARDED_REQUEST_HEADERS = [
  "authorization",
  "content-type",
  "accept",
  "x-workspace-id",
  "x-scheduler-secret",
  "x-requested-with",
];

const isProxiedPath = (pathname: string): boolean =>
  pathname === "/api" || pathname.startsWith("/api/") || pathname === "/health";

/**
 * Proxy mot request sang backend.
 *
 * `redirect: "manual"` de Worker khong di theo redirect cua backend: neu
 * endpoint tra 307/308, ta phai tra nguyen cho client de trinh duyet theo
 * dung dia chi backend, khong phai noi trong Worker.
 */
async function proxyToBackend(request: Request, env: Env): Promise<Response> {
  const origin = env.BACKEND_ORIGIN?.replace(/\/+$/, "");
  if (!origin) {
    return Response.json(
      {
        detail:
          "Chua cau hinh BACKEND_ORIGIN. Dat bang: wrangler secret put BACKEND_ORIGIN",
      },
      { status: 503 },
    );
  }

  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, origin);

  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const hasBody = !["GET", "HEAD"].includes(request.method);

  try {
    return await fetch(new Request(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      redirect: "manual",
      // Cloudflare Worker khong dung signal cua request goc.
      ...(request as unknown as { cf?: RequestInitCfProperties }).cf
        ? { cf: (request as unknown as { cf?: RequestInitCfProperties }).cf }
        : {},
    }));
  } catch (error) {
    return Response.json(
      {
        detail:
          "Khong ket noi duoc backend. Backend co the dang cold-start; thu lai sau vai giay.",
        backend_error: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (isProxiedPath(pathname)) {
      return proxyToBackend(request, env);
    }
    return env.ASSETS.fetch(request);
  },

  /**
   * Cron Trigger: danh thuc scheduler cua backend Render.
   *
   * `controller.cron` la CHUOI bieu thuc cron, khong phai ten tu dat — khop
   * sai thi handler thoat ngay va lich khong bao gio chay.
   */
  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    if (controller.cron !== SCHEDULER_CRON_EXPRESSION) return;

    const origin = env.BACKEND_ORIGIN?.replace(/\/+$/, "");
    if (!origin) {
      console.error(
        "[scheduler] BACKEND_ORIGIN chua duoc cau hinh — bo qua lan chay cron nay.",
      );
      return;
    }
    if (!env.SCHEDULER_SECRET) {
      console.error(
        "[scheduler] SCHEDULER_SECRET chua duoc cau hinh — bo qua lan chay cron nay.",
      );
      return;
    }

    ctx.waitUntil(
      (async () => {
        try {
          const response = await fetch(
            `${origin}/api/v1/schedules/trigger-worker`,
            {
              method: "POST",
              headers: { "X-Scheduler-Secret": env.SCHEDULER_SECRET },
            },
          );
          if (!response.ok) {
            console.error(
              `Scheduler run failed with status ${response.status}: ${await response.text()}`,
            );
          }
        } catch (error) {
          // Nem loi de Cloudflare retry theo lich, tranh bo lot mot vong doi
          // scheduler khi backend dang cold-start.
          console.error("Scheduled content publish failed", error);
          throw error;
        }
      })(),
    );
  },
};