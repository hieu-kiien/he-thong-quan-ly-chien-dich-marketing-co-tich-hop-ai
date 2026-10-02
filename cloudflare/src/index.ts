import { Container, getContainer } from "@cloudflare/containers";

const DATABASE_BACKUP_KEY = "marketflow/production.sqlite";
const API_PORT = 8000;
const CONTROL_PORT = 8001;

interface Env {
  API: DurableObjectNamespace<FastApiContainer>;
  ASSETS: Fetcher;
  DATABASE_BACKUPS: R2Bucket;
  SECRET_KEY: string;
  JWT_SECRET_KEY: string;
  BYOK_ENCRYPTION_KEY: string;
  // P0: thieu binding nay thi moi request AI tren Cloudflare deu khong co key ->
  // im lang rot ve Smart Fallback. Xem `secrets.required` trong wrangler.jsonc.
  AI_API_KEY: string;
  MARKETFLOW_MANAGER_PASSWORD: string;
  MARKETFLOW_MARKETER_PASSWORD: string;
  MARKETFLOW_APPROVER_PASSWORD: string;
  /** Xác thực cho cron gọi POST /api/v1/schedules/trigger-worker. */
  SCHEDULER_SECRET: string;
}

/**
 * Biểu thức cron của lịch đăng nội dung, phải khớp `triggers.crons` trong
 * wrangler.jsonc.
 *
 * `ScheduledController.cron` là CHUỖI BIỂU THỨC CRON (mẫu "mỗi 5 phút"), không
 * phải tên do ta tự đặt. Trước đây hằng này là "scheduled-content-publish" và
 * handler so khớp với nó, nên điều kiện luôn sai -> `scheduled()` thoát ngay và
 * lịch đăng trên Cloudflare KHÔNG BAO GIỜ chạy, trong khi container đã tắt
 * scheduler nên cũng không có đường thay thế. Lịch sẽ tích tụ rồi mất khi
 * container bị evict, đúng thứ mà cấu hình này sinh ra để tránh.
 */
const SCHEDULER_CRON_EXPRESSION = "*/5 * * * *";

export class FastApiContainer extends Container<Env> {
  defaultPort = CONTROL_PORT;
  sleepAfter = "10m";
  private backups: R2Bucket;
  // TODO(ky thuat no - CHUA xu ly, chi ghi nhan de khong bi quen):
  //   1) `writeQueue` serialize MOI write (POST/PUT/PATCH/DELETE) ve mot hang
  //      doi mot. Dung de tranh ghi chong, nhung moi request ghi deu phai CHO
  //      het request ghi truoc do. Voi `max_instances: 1` trong wrangler.jsonc
  //      thi day la hang doi toan cuc cua he thong: mot request cham bien co
  //      lam tat ca nguoi dung khac bi treo theo (latency phep toan cuc).
  //   2) `persistSnapshot()` goi GET /snapshot tren container roi PUT TOAN BO
  //      DB len R2 sau MOI write. Chi phi ghi la O(db size) + 1 network round
  //      toi R2 cho moi thao tac ghi. DB lon 100 MB = 100 MB + 100 MB upload
  //      cho moi click, latency ghi tang tuyet doi theo duong cong dung.
  //   3) Hai dieu tren la ly do thay doi kien truc (incremental/append-only R2
  //      log + periodic compaction, hoac Durable Object storage thay R2) ma
  //      KHONG sua o day de giu pham vi patch hien tai it rui ro.
  //   Han ghi cho lan sua tiep theo: bao dam moi thay doi khong lam mat "durability"
  //   hien tai (write tra 503 neu snapshot that bai) va khong bo qua
  //   `brandKitReadCreatesRecord` o fetch() - GET /api/v1/brand-kit la read
  //   nhung lai tao record, nen phai di qua write path.
  private writeQueue: Promise<unknown> = Promise.resolve();

  constructor(ctx: DurableObjectState<Env>, env: Env) {
    super(ctx, env);
    this.backups = env.DATABASE_BACKUPS;
    this.envVars = {
      APP_ENV: "production",
      DATABASE_URL: "sqlite:////app/data/marketing_campaigns.db",
      SECRET_KEY: env.SECRET_KEY,
      JWT_SECRET_KEY: env.JWT_SECRET_KEY,
      BYOK_ENCRYPTION_KEY: env.BYOK_ENCRYPTION_KEY,
      // P0: truyen AI_API_KEY vao container. Khong co dong nay, moi request AI
      // tren Cloudflare deu khong co key va im lang rot ve Smart Fallback.
      AI_API_KEY: env.AI_API_KEY,
      MARKETFLOW_MANAGER_PASSWORD: env.MARKETFLOW_MANAGER_PASSWORD,
      MARKETFLOW_MARKETER_PASSWORD: env.MARKETFLOW_MARKETER_PASSWORD,
      MARKETFLOW_APPROVER_PASSWORD: env.MARKETFLOW_APPROVER_PASSWORD,
      // QUAN TRỌNG: tắt scheduler trong container. Scheduler ghi thẳng vào
      // SQLite mà không đi qua HTTP, nên thay đổi đó không bao giờ được
      // `persistSnapshot()` đẩy lên R2. Container evict sau `sleepAfter` là
      // mọi bài đã "đăng" biến mất âm thầm, không có lỗi nào được ghi.
      // Lịch đăng được xử lý ở `scheduled()` bên dưới rồi mới snapshot.
      SCHEDULER_ENABLED: "false",
      SCHEDULER_SECRET: env.SCHEDULER_SECRET,
    };
  }

  override async onStart(): Promise<void> {
    const previous = await this.backups.get(DATABASE_BACKUP_KEY);
    const restoreBytes = previous ? await previous.arrayBuffer() : undefined;
    const bootstrap = await this.containerFetch(
      "http://localhost/bootstrap",
      { method: "POST", body: restoreBytes },
      CONTROL_PORT,
    );
    if (!bootstrap.ok) {
      throw new Error(`FastAPI bootstrap failed with status ${bootstrap.status}`);
    }
    await this.persistSnapshot();
  }

  /**
   * Xử lý lịch đăng định kỳ. Gọi từ Cron Trigger của Worker.
   *
   * Đây là đường DUY NHẤT được phép chạy scheduler trên Cloudflare: nó đi qua
   * cùng cơ chế hàng đợi + snapshot như một request ghi bình thường, nên kết quả
   * được bền vững trên R2. Container nền phải tắt scheduler (SCHEDULER_ENABLED).
   */
  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    // Đọc secret từ `env` của lời gọi chứ không qua `this.envVars`: kiểu của
    // `envVars` là partial nên truy cập thuộc tính bị coi là có thể `undefined`.
    // `env.SCHEDULER_SECRET` là binding bắt buộc nên kiểm tra tại đây là kiểm tra
    // lúc chạy — Worker vẫn khởi động bình thường, chỉ log cảnh báo.
    const schedulerSecret = env.SCHEDULER_SECRET;
    if (!schedulerSecret) {
      console.error(
        "[scheduler] SCHEDULER_SECRET chưa được cấu hình — bỏ qua lần chạy cron này. " +
          "Đặt secret bằng: wrangler secret put SCHEDULER_SECRET",
      );
      return;
    }
    ctx.waitUntil(
      (async () => {
        try {
          const response = await this.containerFetch(
            "http://127.0.0.1/api/v1/schedules/trigger-worker",
            {
              method: "POST",
              headers: { "X-Scheduler-Secret": schedulerSecret },
            },
            API_PORT,
          );
          if (!response.ok) {
            console.error(
              `Scheduler run failed with status ${response.status}: ${await response.text()}`,
            );
            return;
          }
          // Chỉ snapshot khi thực sự có việc cần ghi. Gọi snapshot sau mỗi lần chạy
          // kể cả khi không có lịch đến hạn sẽ tải toàn bộ DB lên R2 vô ích.
          const payload = (await response.clone().json()) as { count?: number };
          if ((payload.count ?? 0) > 0) {
            await this.persistSnapshot();
          }
        } catch (error) {
          console.error("Scheduled content publish failed", error);
          throw error; // để Cloudflare retry theo lịch
        }
      })(),
    );
  }

  override async fetch(request: Request): Promise<Response> {
    const pathname = new URL(request.url).pathname.replace(/\/+$/, "");
    const brandKitReadCreatesRecord =
      ["GET", "HEAD"].includes(request.method) && pathname === "/api/v1/brand-kit";
    if (["GET", "HEAD", "OPTIONS"].includes(request.method) && !brandKitReadCreatesRecord) {
      return this.containerFetch(request, API_PORT);
    }

    const operation = this.writeQueue.then(() => this.forwardWrite(request));
    this.writeQueue = operation.catch(() => undefined);
    return operation;
  }

  private async forwardWrite(request: Request): Promise<Response> {
    const response = await this.containerFetch(request, API_PORT);
    try {
      await this.persistSnapshot();
      return response;
    } catch (error) {
      console.error("Database snapshot failed after API write", error);
      return Response.json(
        { detail: "Không thể xác nhận lưu bền vững dữ liệu. Vui lòng tải lại trước khi thử lại." },
        { status: 503 },
      );
    }
  }

  private async persistSnapshot(): Promise<void> {
    const snapshot = await this.containerFetch(
      "http://localhost/snapshot",
      { method: "GET" },
      CONTROL_PORT,
    );
    if (!snapshot.ok || !snapshot.body) {
      throw new Error(`Database snapshot endpoint returned ${snapshot.status}`);
    }
    await this.backups.put(DATABASE_BACKUP_KEY, snapshot.body, {
      httpMetadata: { contentType: "application/vnd.sqlite3" },
    });
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (pathname === "/api" || pathname.startsWith("/api/") || pathname === "/health") {
      const backend = getContainer(env.API, "marketflow-production");
      return backend.fetch(request);
    }
    return env.ASSETS.fetch(request);
  },

  /**
   * Cron Trigger: đẩy việc xử lý lịch đăng xuống Durable Object.
   *
   * Nếu không có handler này, lịch đăng trên Cloudflare sẽ KHÔNG BAO GIỜ được
   * chạy — vì scheduler trong container đã bị tắt (SCHEDULER_ENABLED=false) để
   * tránh mất dữ liệu do không snapshot. `ctx.waitUntil` để không chặn response
   * của cron trigger; lỗi vẫn được log trong DO.
   */
  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    // So khớp theo biểu thức cron, không theo tên tự đặt — xem SCHEDULER_CRON_EXPRESSION.
    if (controller.cron !== SCHEDULER_CRON_EXPRESSION) return;
    const backend = getContainer(env.API, "marketflow-production");
    ctx.waitUntil(backend.scheduled(controller, env, ctx));
  },
};
