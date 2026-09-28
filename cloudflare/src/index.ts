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
}

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
};
