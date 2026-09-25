import { Container, getContainer } from "@cloudflare/containers";

const DATABASE_BACKUP_KEY = "marketflow/production.sqlite";
const API_PORT = 8000;
const CONTROL_PORT = 8001;

interface Env {
  API: DurableObjectNamespace<FastApiContainer>;
  ASSETS: Fetcher;
  DATABASE_BACKUPS: R2Bucket;
  SECRET_KEY: string;
  MARKETFLOW_MANAGER_PASSWORD: string;
  MARKETFLOW_MARKETER_PASSWORD: string;
  MARKETFLOW_APPROVER_PASSWORD: string;
}

export class FastApiContainer extends Container<Env> {
  defaultPort = CONTROL_PORT;
  sleepAfter = "10m";
  private backups: R2Bucket;
  private writeQueue: Promise<unknown> = Promise.resolve();

  constructor(ctx: DurableObjectState<Env>, env: Env) {
    super(ctx, env);
    this.backups = env.DATABASE_BACKUPS;
    this.envVars = {
      APP_ENV: "production",
      DATABASE_URL: "sqlite:////app/data/marketing_campaigns.db",
      SECRET_KEY: env.SECRET_KEY,
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
