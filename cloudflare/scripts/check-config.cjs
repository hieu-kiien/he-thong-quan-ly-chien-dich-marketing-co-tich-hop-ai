const fs = require("fs");

/**
 * Strip comment trong JSONC ma KHONG du vao string literal.
 *
 * Regex nao cung duoc bo qua o day: `/\\/\\/.*$/gm` se cat con trong
 * "https://..." — chu `//` trong URL la ky tu thuong, khong phai comment.
 * Do do phai quet char-by-char, nho trang thai dang o trong string.
 */
function stripJsoncComments(input) {
  let out = "";
  let inString = false;
  let escaped = false;
  let inLine = false;
  let inBlock = false;

  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    const next = input[i + 1];

    if (inLine) {
      if (c === "\n") { inLine = false; out += c; }
      continue;
    }
    if (inBlock) {
      if (c === "*" && next === "/") { inBlock = false; i++; }
      else if (c === "\n") out += c;
      continue;
    }
    if (inString) {
      out += c;
      if (escaped) escaped = false;
      else if (c === "\\") escaped = true;
      else if (c === '"') inString = false;
      continue;
    }

    if (c === '"') { inString = true; out += c; continue; }
    if (c === "/" && next === "/") { inLine = true; i++; continue; }
    if (c === "/" && next === "*") { inBlock = true; i++; continue; }
    out += c;
  }
  return out;
}

const raw = stripJsoncComments(fs.readFileSync("wrangler.jsonc", "utf8"));
const cfg = JSON.parse(raw);

const required = (cfg.secrets && cfg.secrets.required) || [];
const vars = cfg.vars || {};
console.log("secrets.required =", required.join(", "));
console.log("vars =", Object.keys(vars).join(", "));

const requiredNow = ["BACKEND_ORIGIN", "SCHEDULER_SECRET"];
const missingSecrets = requiredNow.filter((k) => !(k in vars) || !vars[k]).filter(
  (k) => !required.includes(k),
);
if (missingSecrets.length) {
  console.error(
    "::error::thieu khai bao cho " + missingSecrets.join(", ") +
      " (Worker se tra 503 hoac bo qua cron)",
  );
  process.exit(1);
}

const crons = (cfg.triggers && cfg.triggers.crons) || [];
const src = fs.readFileSync("src/index.ts", "utf8");
const m = src.match(/SCHEDULER_CRON_EXPRESSION\s*=\s*["']([^"']+)["']/);
if (!m) {
  console.error("::error::khong tim thay SCHEDULER_CRON_EXPRESSION trong src/index.ts");
  process.exit(1);
}
if (!crons.includes(m[1])) {
  console.error(
    '::error::Worker so sanh cron "' + m[1] + '" nhung triggers.crons la: ' + JSON.stringify(crons),
  );
  process.exit(1);
}
console.log("cron khop: " + m[1]);

// Backend da chuyen ra Render nen binding container phai bi goi het. Neu con
// `containers`/`durable_objects`, len deploy se tra 401 "Workers Paid plan"
// va moi route /api/* se 404.
const stale = ["containers", "durable_objects", "migrations", "r2_buckets"].filter(
  (k) => cfg[k],
);
if (stale.length) {
  console.error(
    "::error::wrangler.jsonc van con binding Cloudflare Container (" +
      stale.join(", ") +
      "). Tai khoan nay khong co Workers Paid plan nen deploy se fail. Backend chay o Render.",
  );
  process.exit(1);
}

console.log("wrangler config OK");