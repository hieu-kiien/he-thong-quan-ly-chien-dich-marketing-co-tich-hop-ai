const fs = require("fs");

const raw = fs.readFileSync("wrangler.jsonc", "utf8").replace(/\/\/.*$/gm, "");
const cfg = JSON.parse(raw);

const required = (cfg.secrets && cfg.secrets.required) || [];
console.log("secrets.required =", required.join(", "));
if (!required.includes("SCHEDULER_SECRET")) {
  console.error("::error::SCHEDULER_SECRET phai nam trong secrets.required");
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
console.log("wrangler config OK");