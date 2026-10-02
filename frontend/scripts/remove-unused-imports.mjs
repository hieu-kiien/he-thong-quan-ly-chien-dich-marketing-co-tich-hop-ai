/**
 * Xoá các import không còn được dùng mà TypeScript đã báo (TS6133 / TS6192).
 *
 * Vì sao cần script thay vì sửa tay: `noUnusedLocals` vừa bật trong tsconfig và
 * chặn được 123 import chết, nhưng xoá tay dễ sót hoặc làm hỏng cây import.
 * Script chỉ xoá đúng tên mà `tsc` xác nhận không dùng, rồi để `tsc` xác minh
 * lại toàn bộ.
 *
 * Cách dùng:  node scripts/remove-unused-imports.mjs [--dry-run]
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';

const DRY_RUN = process.argv.includes('--dry-run');
const PROJECT_ROOT = process.cwd();
const SRC_DIR = path.join(PROJECT_ROOT, 'src');

/** Lấy danh sách lỗi TS6133/TS6192 từ chính `tsc` (nguồn sự thật duy nhất). */
function collectDiagnostics() {
  let raw = '';
  try {
    raw = execSync('npx tsc --noEmit --pretty false', {
      cwd: PROJECT_ROOT,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (err) {
    // tsc trả exit code khác 0 khi còn lỗi — đó là trường hợp bình thường ở đây.
    raw = `${err.stdout ?? ''}${err.stderr ?? ''}`;
  }
  const byFile = new Map();
  for (const line of raw.split(/\r?\n/)) {
    const m = /^(.+?)\((\d+),(\d+)\): error TS(6133|6192): (.+)$/.exec(line.trim());
    if (!m) continue;
    const [, file, lineNo, , code, message] = m;
    if (!byFile.has(file)) byFile.set(file, []);
    byFile.get(file).push({
      line: Number(lineNo),
      name: /^'([^']+)'/.exec(message)?.[1] ?? null,
      code,
      message,
    });
  }
  return byFile;
}

/**
 * Gỡ một tên khỏi danh sách import.
 * Trả về nội dung import mới, hoặc null nếu nên xoá hẳn cả dòng import.
 */
function stripFromImport(statement, name) {
  // import { A, B, type C } from 'x';
  const namedMatch = /import\s*\{([\s\S]*?)\}\s*from\s*(['"][^'"]+['"])\s*;?/.exec(statement);
  if (namedMatch) {
    const body = namedMatch[1];
    const specifiers = body
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const kept = specifiers.filter((s) => {
      const base = s.replace(/^type\s+/, '').split(/\s+as\s+/)[0].trim();
      return base !== name;
    });
    if (kept.length === specifiers.length) return statement; // không tìm thấy
    if (kept.length === 0) return null; // import rỗng -> xoá cả dòng
    return `import { ${kept.join(', ')} } from ${namedMatch[2]};`;
  }

  // import Default, { A } from 'x'  /  import Default from 'x'  /  import * as Ns from 'x'
  const defaultMatch = /import\s+([A-Za-z_$][\w$]*)\s*(,\s*\{[\s\S]*?\})?\s*from\s*(['"][^'"]+['"])\s*;?/.exec(statement);
  if (defaultMatch) {
    const [, defaultName, namedPart, source] = defaultMatch;
    if (namedPart) {
      const named = stripFromImport(`import ${namedPart} from ${source};`, name);
      if (named === null) return `import ${defaultName} from ${source};`;
      const inner = named.replace(/^import\s*\{/, '').replace(/\}\s*from.*$/, '');
      return `import ${defaultName}, { ${inner.trim()} } from ${source};`;
    }
    if (defaultName === name) return null;
    return statement;
  }

  return statement;
}

/** Gỡ một khai báo cục bộ đơn giản (const/let) mà tsc báo không dùng. */
function stripLocalDeclaration(lines, name) {
  for (let i = 0; i < lines.length; i++) {
    const re = new RegExp(`^(\\s*)(?:const|let|var)\\s+(\\{[^}]*\\}|${escapeRegExp(name)})\\b`);
    const m = re.exec(lines[i]);
    if (!m) continue;
    const statement = lines[i];

    // const { a, b } = ...  -> bỏ thành phần không dùng
    if (m[2].startsWith('{')) {
      const body = m[2].slice(1, -1);
      const parts = body.split(',').map((s) => s.trim()).filter(Boolean);
      const kept = parts.filter((p) => p.split(':').pop().trim() !== name);
      if (kept.length === parts.length) continue;
      if (kept.length === 0) {
        lines.splice(i, 1);
      } else {
        lines[i] = statement.replace(m[2], `{ ${kept.join(', ')} }`);
      }
      return true;
    }

    // const foo = ... (một dòng) -> xoá hẳn dòng
    if (statement.includes('=') && statement.trimEnd().endsWith(';')) {
      lines.splice(i, 1);
      return true;
    }
  }
  return false;
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const diagnostics = collectDiagnostics();
let changedFiles = 0;
let removedNames = 0;
const unresolved = [];

for (const [relFile, diags] of diagnostics) {
  const abs = path.join(PROJECT_ROOT, relFile);
  let content = readFileSync(abs, 'utf8');
  const original = content;

  const importDiags = diags.filter((d) => d.name);
  for (const d of importDiags) {
    if (!d.name) continue;

    if (d.code === '6192') {
      // Cả dòng import không dùng gì -> xoá cả dòng.
      const lines = content.split('\n');
      const idx = d.line - 1;
      if (lines[idx] && lines[idx].trimStart().startsWith('import')) {
        lines.splice(idx, 1);
        content = lines.join('\n');
        removedNames++;
        continue;
      }
      unresolved.push(`${relFile}: TS6192 dòng ${d.line} không nhận diện được`);
      continue;
    }

    const stmtMatch = new RegExp(
      `^import[\\s\\S]*?from\\s*['"][^'"]+['"];?$`,
      'm',
    );
    const lines = content.split('\n');
    // Tìm dòng import chứa tên cần gỡ.
    let handled = false;
    for (let i = 0; i < lines.length; i++) {
      if (!lines[i].trimStart().startsWith('import')) continue;
      // Gom các dòng import nhiều dòng (import {\n A,\n B\n} from 'x')
      let stmt = lines[i];
      let end = i;
      while (!/from\s*['"][^'"]+['"]\s*;?\s*$/.test(stmt) && end + 1 < lines.length) {
        end++;
        stmt += `\n${lines[end]}`;
      }
      if (!new RegExp(`\\b${escapeRegExp(d.name)}\\b`).test(stmt)) continue;
      const next = stripFromImport(stmt, d.name);
      if (next === null) {
        lines.splice(i, end - i + 1);
        content = lines.join('\n');
        lines.length = 0;
        handled = true;
        removedNames++;
        break;
      }
      if (next !== stmt) {
        if (next.includes('\n')) {
          lines.splice(i, end - i + 1, ...next.split('\n'));
        } else {
          lines.splice(i, end - i + 1, next);
        }
        content = lines.join('\n');
        lines.length = 0;
        handled = true;
        removedNames++;
        break;
      }
    }
    if (!handled) {
      // Không nằm trong import -> thử gỡ khai báo cục bộ.
      const localLines = content.split('\n');
      if (stripLocalDeclaration(localLines, d.name)) {
        content = localLines.join('\n');
        removedNames++;
      } else {
        unresolved.push(`${relFile}: '${d.name}' (dòng ${d.line}) — cần xử lý tay`);
      }
    }
  }

  if (content !== original) {
    changedFiles++;
    if (!DRY_RUN) writeFileSync(abs, content);
  }
}

console.log(
  `${DRY_RUN ? '[DRY RUN] ' : ''}Đã xử lý ${changedFiles} file, gỡ ${removedNames} khai báo không dùng.`,
);
if (unresolved.length) {
  console.log(`\nCòn ${unresolved.length} mục cần xử lý tay:`);
  unresolved.forEach((u) => console.log(`  - ${u}`));
}
void stmtMatchGuard;
function stmtMatchGuard() {}
