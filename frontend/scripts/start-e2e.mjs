#!/usr/bin/env node
/**
 * start-e2e.mjs - Khoi dong toan bo stack E2E (backend THAT + frontend THAT).
 *
 * VI SAO FILE NAY TON TAI
 * ----------------------
 * Playwright chi ho tro MOT `webServer` trong config, nhung bai E2E nay can HAI
 * tien trinh: uvicorn (FastAPI) va `vite preview`. Truoc day config chi chay
 * `npm run preview` (mot bundle tinh, khong co backend), nen toan bo test chi
 * kiem tra UI tren DU LIEU GIA do `mock-api.ts` inject. File nay gom hai tien
 * trinh vao mot supervisor de Playwright co the theo doi bang mot `url` duy nhat.
 *
 * HAI CHE DO (E2E_MODE)
 * ---------------------
 * - `E2E_MODE=live`  : backend that + BUILD LAI frontend voi VITE_API_URL tro
 *                      toi backend that, roi preview. Bat ky request API nao
 *                      cung khong bi intercept => test chay tren du lieu that.
 *   - `E2E_MODE=mock` : chi preview bundle hien co (khong can backend, chay
 *                      offline, nhanh). Mac dinh de khong phai moi nguoi
 *                      deu phai co Python khi chi muon chay UI regression.
 *
 * BIEN MOI TRUONG
 * ---------------
 * - E2E_MODE                    : 'mock' | 'live'           (mac dinh 'mock')
 * - E2E_BACKEND_PORT            : co backend that             (mac dinh 8000)
 * - E2E_FRONTEND_PORT           : co preview                  (mac dinh 4173)
 * - E2E_PYTHON                  : interpreter                 (mac dinh python / python3)
 * - E2E_BACKEND_READY_TIMEOUT_MS: cho backend healthy         (mac dinh 90000)
 * - E2E_AI_API_KEY              : de rong mac dinh => AI dung fallback
 *                                 xac dinh, E2E khong phu thuoc mang ngoai
 * - E2E_SKIP_BUILD              : '1' de bo qua `npm run build` (chi khi dist
 *                                 da duoc build dung cach)
 */

import { spawn, execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function killPort(port) {
  try {
    if (process.platform === 'win32') {
      const out = execSync(`netstat -ano -p tcp`, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
      const lines = out.split(/\r?\n/).filter(line => line.includes(`:${port}`) && line.includes('LISTENING'));
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && pid !== '0' && Number(pid) !== process.pid) {
          try {
            execSync(`taskkill /F /T /PID ${pid}`, { stdio: 'ignore' });
          } catch {}
        }
      }
    } else {
      try {
        execSync(`fuser -k -9 ${port}/tcp 2>/dev/null || true`, { stdio: 'ignore' });
      } catch {}
      try {
        execSync(`lsof -ti:${port} | xargs -r kill -9 2>/dev/null || true`, { stdio: 'ignore' });
      } catch {}
    }
  } catch {}
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, '..');
const BACKEND_DIR = path.resolve(FRONTEND_DIR, '..', 'backend');

const IS_WINDOWS = process.platform === 'win32';

const MODE = (process.env.E2E_MODE || 'mock').toLowerCase();
const IS_LIVE = MODE === 'live';

const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = Number(process.env.E2E_BACKEND_PORT || 8000);
const FRONTEND_HOST = '127.0.0.1';
const FRONTEND_PORT = Number(process.env.E2E_FRONTEND_PORT || 4173);

const API_BASE_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1`;
const HEALTH_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/health`;
const BACKEND_READY_TIMEOUT_MS = Number(process.env.E2E_BACKEND_READY_TIMEOUT_MS || 90_000);

const NPM_CMD = IS_WINDOWS ? 'npm.cmd' : 'npm';
const PYTHON_CMD =
  process.env.E2E_PYTHON || (IS_WINDOWS ? 'python' : 'python3');

// Node >= 18.20 / 20.12 (fix CVE-2024-27980) throw `spawn EINVAL` khi spawn
// truc tiep file `.cmd`/`.bat` (chinh la `npm.cmd` tren Windows) ma khong bat
// shell. Tren Windows phai de `shell: true`; tren POSIX `npm` la shell script
// co shebang nen `shell: false` van chay duoc va giu process group sach.
const USE_SHELL = IS_WINDOWS;

/** @type {Array<{name: string, child: import('node:child_process').ChildProcess}>} */
const managed = [];
let shuttingDown = false;

function log(step, message) {
  process.stdout.write(`[start-e2e][${step}] ${message}\n`);
}

function warn(step, message) {
  process.stderr.write(`[start-e2e][${step}] WARN: ${message}\n`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Chay mot lenh "chay toi completion", reject neu exit code khac 0. */
function runToCompletion(name, command, args, options = {}) {
  return new Promise((resolve, reject) => {
    log(name, `$ ${command} ${args.join(' ')}`);
    const child = spawn(command, args, {
      cwd: options.cwd || FRONTEND_DIR,
      env: { ...process.env, ...(options.env || {}) },
      stdio: 'inherit',
      shell: USE_SHELL,
    });
    child.on('error', (err) => reject(new Error(`${name}: khong chay duoc "${command}": ${err.message}`)));
    child.on('exit', (code, signal) => {
      if (code === 0) {
        log(name, 'hoan tat OK');
        resolve();
      } else {
        reject(new Error(`${name}: exit code=${code} signal=${signal}`));
      }
    });
  });
}

/** Khoi dong mot tien trinh song dai va giu lai de cuoi cung bi doi chung. */
function launch(name, command, args, options = {}) {
  log(name, `$ ${command} ${args.join(' ')}`);
  const child = spawn(command, args, {
    cwd: options.cwd || FRONTEND_DIR,
    env: { ...process.env, ...(options.env || {}) },
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: USE_SHELL,
    // POSIX: `detached` tao mot process group rieng de `kill(-pid)` gat duoc
    // ca uvicorn con (reload worker) lan npm -> node -> vite preview.
    detached: !IS_WINDOWS,
  });
  managed.push({ name, child });

  const prefix = (stream, target) => {
    stream.setEncoding('utf8');
    let buffer = '';
    stream.on('data', (chunk) => {
      buffer += chunk;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (line.trim().length > 0) target.write(`[${name}] ${line}\n`);
      }
    });
  };
  prefix(child.stdout, process.stdout);
  prefix(child.stderr, process.stderr);

  child.on('error', (err) => warn(name, `khong chay duoc "${command}": ${err.message}`));
  child.on('exit', (code, signal) => {
    log(name, `ket thuc (code=${code} signal=${signal})`);
    if (!shuttingDown) {
      // Tien trinh con chet ngay lap tuc nghia khong the phuc vu test nua.
      warn(name, 'tien trinh da dung trong khi bo cuc chua ket thuc.');
      void shutdown(1);
    }
  });

  return child;
}

/** Giu nguyen process: khong dung `exec`, vi uvicorn spawn them worker con. */
function killTree(child) {
  if (!child || child.killed || child.exitCode !== null) return;
  const pid = child.pid;
  if (!pid) return;
  try {
    if (IS_WINDOWS) {
      // taskkill /T giet ca cay tien trinh con (npm.cmd -> node -> vite).
      spawn('taskkill', ['/F', '/T', '/PID', String(pid)], { stdio: 'ignore' });
    } else {
      // ESCHUA process group (vi detached: true) roi giet ca nhom.
      process.kill(-pid, 'SIGTERM');
    }
  } catch (err) {
    warn('shutdown', `khong gui tin hieu tat cho pid=${pid}: ${err.message}`);
  }
}

async function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  log('shutdown', `tat ${managed.length} tien trinh...`);
  for (const { child } of managed.reverse()) {
    killTree(child);
  }
  if (IS_LIVE) {
    killPort(BACKEND_PORT);
  }
  killPort(FRONTEND_PORT);
  // Cho uvicorn/vite dong file DB va flush stdout truoc khi process cha bi ket.
  await sleep(700);
  process.exit(code);
}

process.on('SIGINT', () => void shutdown(0));
process.on('SIGTERM', () => void shutdown(0));
process.on('SIGHUP', () => void shutdown(0));
// Playwright/Windows co the buoc "end task tree"; handler nay bao dam con khong
// bi orphan du chinh process cha da bi kill.
process.on('exit', () => {
  for (const { child } of managed) killTree(child);
});
process.on('uncaughtException', (err) => {
  warn('fatal', err && err.stack ? err.stack : String(err));
  void shutdown(1);
});
process.on('unhandledRejection', (err) => {
  warn('fatal', err && err.stack ? err.stack : String(err));
  void shutdown(1);
});

async function waitForHttpOk(url, timeoutMs, label) {
  const startedAt = Date.now();
  let attempt = 0;
  let lastError = '';
  while (Date.now() - startedAt < timeoutMs) {
    attempt += 1;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timer);
      if (res.status >= 200 && res.status < 400) {
        log('ready', `${label} healthy sau ${((Date.now() - startedAt) / 1000).toFixed(1)}s (${attempt} lan thu) -> ${url}`);
        return;
      }
      lastError = `HTTP ${res.status}`;
    } catch (err) {
      lastError = err && err.message ? err.message : String(err);
    }
    if (attempt % 5 === 0) {
      log('wait', `${label} chua san sang (${((Date.now() - startedAt) / 1000).toFixed(0)}s/${(timeoutMs / 1000).toFixed(0)}s) - ${lastError}`);
    }
    await sleep(500);
  }
  throw new Error(`${label} khong healthy sau ${timeoutMs}ms. Loi cuoi cung: ${lastError}`);
}

async function startBackend() {
  if (!existsSync(BACKEND_DIR)) {
    throw new Error(`Khong tim thay backend tai ${BACKEND_DIR}`);
  }

  // APP_ENV=test: giup khoi tao DB + nap seed data mau (khong phai production),
  // nho do login manager@gmail.com / Manager@123 hoat dong.
  // AI_API_KEY rong => ai_service bo qua provider that va dung fallback xac dinh
  // (xem app/services/ai/ai_service.py dong ~605). E2E vì vay khong phu thuoc
  // mang ngoai va khong bao gio timeout vi goi LLM that.
  const env = {
    APP_ENV: process.env.APP_ENV || 'test',
    DATABASE_URL: process.env.DATABASE_URL || 'sqlite:///./data/marketing_campaigns.db',
    AI_ENABLE_FALLBACK: 'true',
    AI_API_KEY: process.env.E2E_AI_API_KEY || '',
    AI_TIMEOUT_SECONDS: process.env.E2E_AI_TIMEOUT || '10',
  };

  log('backend', `APP_ENV=${env.APP_ENV} DATABASE_URL=${env.DATABASE_URL}`);
  log('backend', `AI provider: ${env.AI_API_KEY ? 'khoa that (E2E_AI_API_KEY)' : 'khong co khoa -> fallback xac dinh'}`);

  launch(
    'backend',
    PYTHON_CMD,
    ['-m', 'uvicorn', 'app.main:app', '--host', BACKEND_HOST, '--port', String(BACKEND_PORT)],
    { cwd: BACKEND_DIR, env }
  );

  await waitForHttpOk(HEALTH_URL, BACKEND_READY_TIMEOUT_MS, 'backend');
}

async function buildFrontend() {
  if (String(process.env.E2E_SKIP_BUILD || '') === '1') {
    log('build', 'bo qua theo E2E_SKIP_BUILD=1');
    return;
  }
  // VITE nung gia tri env luc BUILD, khong phai luc preview.
  //
  // LIVE: build tro toi backend that.
  // MOCK: build voi DUONG DAN TUONG DOI `/api/v1` (cung origin voi preview).
  //   Bat buoc phai build lai, KHONG dung lai bundle hien co. Ly do: VITE_API_URL
  //   duoc nung vao JS bundle luc build. Neu lan truoc da build o LIVE mode
  //   (VITE_API_URL=http://127.0.0.1:8000/api/v1) roi chay MOCK mode, bundle do
  //   van tro ve backend that -> request lot ra ngoai, khong co mock nao chan,
  //   browser bao loi CORS va UI render sai du lieu. Test E2E phai co TINH LAP
  //   DINH: ket qua chi phu thuoc E2E_MODE, khong phu thuoc lan build truoc do.
  await runToCompletion('build', NPM_CMD, ['run', 'build'], {
    env: { VITE_API_URL: API_BASE_URL },
  });
}

async function ensureDist() {
  const indexHtml = path.join(FRONTEND_DIR, 'dist', 'index.html');
  if (!existsSync(indexHtml)) {
    log('build', 'dist/index.html khong ton tai -> build mot lan');
    await runToCompletion('build', NPM_CMD, ['run', 'build'], { env: { VITE_API_URL: API_BASE_URL } });
    return;
  }
  // Da co dist: kiem tra VITE_API_URL da nung co dung cho che do hien tai khong.
  // Doc tho bundle (khong can, VITE thay the bien luc build roi bien mat khi
  // preview) -> thay bang cach luon build lai o MOCK mode de chan do chac chan.
  if (IS_LIVE) {
    log('build', 'co dist san -> dung lai (E2E_SKIP_BUILD=1 de build lai neu can)');
  } else {
    log('build', 'MOCK mode: build lai voi VITE_API_URL=/api/v1 de tranh ro du lieu');
    await runToCompletion('build', NPM_CMD, ['run', 'build'], { env: { VITE_API_URL: '/api/v1' } });
  }
}

async function main() {
  log('config', `E2E_MODE=${MODE}`);
  log('config', `frontend preview -> http://${FRONTEND_HOST}:${FRONTEND_PORT}`);
  log('config', IS_LIVE ? `backend that     -> ${API_BASE_URL}` : 'backend that     -> (khong bat, test dung mock)');

  // Clean stale ports before launch
  if (IS_LIVE) {
    killPort(BACKEND_PORT);
  }
  killPort(FRONTEND_PORT);

  if (IS_LIVE) {
    await startBackend();
    await buildFrontend();
  } else {
    await ensureDist();
  }

  launch(
    'preview',
    NPM_CMD,
    ['run', 'preview', '--', '--port', String(FRONTEND_PORT), '--host', FRONTEND_HOST],
    { cwd: FRONTEND_DIR }
  );

  await waitForHttpOk(
    `http://${FRONTEND_HOST}:${FRONTEND_PORT}/`,
    BACKEND_READY_TIMEOUT_MS,
    'frontend preview'
  );

  log('ready', `E2E stack san sang. Che do: ${IS_LIVE ? 'LIVE (du lieu that)' : 'MOCK (du lieu gia)'}`);
  log('ready', 'Tien trinh nay se chay cho den khi Playwright dong no lai.');
}

main().catch((err) => {
  warn('fatal', err && err.stack ? err.stack : String(err));
  void shutdown(1);
});
