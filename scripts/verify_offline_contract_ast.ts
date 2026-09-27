import ts from 'typescript';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const apiTsPath = path.resolve(__dirname, '../frontend/src/services/api.ts');
const sourceCode = fs.readFileSync(apiTsPath, 'utf-8');
const sourceFile = ts.createSourceFile('api.ts', sourceCode, ts.ScriptTarget.Latest, true);

console.log('=====================================================================');
console.log(' AST STATIC AUDIT: frontend/src/services/api.ts (TypeScript Compiler API)');
console.log('=====================================================================');

// 10 domains to check
const targetDomains = [
  'authApi',
  'workspaceApi',
  'brandKitApi',
  'campaignApi',
  'productApi',
  'contentApi',
  'aiApi',
  'analyticsApi',
  'scheduleApi',
  'settingsApi'
];

interface CatchAnalysis {
  domain: string;
  method: string;
  line: number;
  hasResponseCheck: boolean;
  hasOfflineDemoCheck: boolean;
  hasConsoleWarn: boolean;
  leaksLocalStorageBeforeCheck: boolean;
  errorVarName: string;
}

const catchAnalyses: CatchAnalysis[] = [];
const discoveredDomains = new Set<string>();

function visit(node: ts.Node) {
  if (ts.isVariableStatement(node)) {
    for (const decl of node.declarationList.declarations) {
      const varName = decl.name.getText(sourceFile);
      if (targetDomains.includes(varName) && decl.initializer && ts.isObjectLiteralExpression(decl.initializer)) {
        discoveredDomains.add(varName);
        inspectDomain(varName, decl.initializer);
      }
    }
  }
  ts.forEachChild(node, visit);
}

function inspectDomain(domainName: string, objLiteral: ts.ObjectLiteralExpression) {
  for (const prop of objLiteral.properties) {
    if (ts.isPropertyAssignment(prop)) {
      const methodName = prop.name.getText(sourceFile);
      inspectMethod(domainName, methodName, prop.initializer);
    }
  }
}

function inspectMethod(domainName: string, methodName: string, expr: ts.Expression) {
  // Find TryStatements in expr
  function findTries(n: ts.Node) {
    if (ts.isTryStatement(n)) {
      if (n.catchClause) {
        analyzeCatch(domainName, methodName, n.catchClause);
      }
    }
    ts.forEachChild(n, findTries);
  }
  findTries(expr);
}

function analyzeCatch(domain: string, method: string, catchClause: ts.CatchClause) {
  const line = sourceFile.getLineAndCharacterOfPosition(catchClause.getStart(sourceFile)).line + 1;
  const errVar = catchClause.variableDeclaration ? catchClause.variableDeclaration.name.getText(sourceFile) : 'e';
  const catchText = catchClause.block.getText(sourceFile);

  // Check 1: Response check (e?.response or e?.response?.data)
  // Can be `if (e?.response) throw e;` or `if (e?.response?.data) return ...;`
  const hasResponseCheck = (
    catchText.includes(`${errVar}?.response`) ||
    catchText.includes(`${errVar}.response`)
  );

  // Check 2: Offline demo check
  // Must check `!isOfflineDemoEnabled()` and throw
  const hasOfflineDemoCheck = (
    catchText.includes('!isOfflineDemoEnabled()') &&
    catchText.includes(`throw ${errVar}`)
  );

  // Check 3: Console warning
  const hasConsoleWarn = (
    catchText.includes('console.warn(') &&
    catchText.includes('[OFFLINE DEMO]')
  );

  // Check 4: Any localStorage before isOfflineDemoEnabled
  const offlineCheckIndex = catchText.indexOf('isOfflineDemoEnabled()');
  const localStorageIndex = catchText.indexOf('localStorage');
  const leaksLocalStorageBeforeCheck = (
    localStorageIndex !== -1 &&
    offlineCheckIndex !== -1 &&
    localStorageIndex < offlineCheckIndex
  );

  catchAnalyses.push({
    domain,
    method,
    line,
    hasResponseCheck,
    hasOfflineDemoCheck,
    hasConsoleWarn,
    leaksLocalStorageBeforeCheck,
    errorVarName: errVar
  });
}

visit(sourceFile);

console.log(`Discovered ${discoveredDomains.size}/${targetDomains.length} target API domains.`);
console.log(`Analyzed ${catchAnalyses.length} catch blocks across all domains.\n`);

let violationsCount = 0;
for (const item of catchAnalyses) {
  const issues: string[] = [];
  if (!item.hasResponseCheck) issues.push('Missing e?.response check');
  if (!item.hasOfflineDemoCheck) issues.push('Missing !isOfflineDemoEnabled() rethrow');
  if (!item.hasConsoleWarn) issues.push('Missing console.warn with [OFFLINE DEMO]');
  if (item.leaksLocalStorageBeforeCheck) issues.push('localStorage accessed before demo check');

  if (issues.length > 0) {
    violationsCount++;
    console.log(`[-] Line ${item.line} | ${item.domain}.${item.method}: FAIL -> ${issues.join(', ')}`);
  } else {
    console.log(`[+] Line ${item.line} | ${item.domain}.${item.method}: PASS (Response Guarded, Offline Rethrown, Demo Warned)`);
  }
}

console.log('\n=====================================================================');
console.log(`TOTAL CATCH BLOCKS AUDITED: ${catchAnalyses.length}`);
console.log(`PASSED: ${catchAnalyses.length - violationsCount}`);
console.log(`VIOLATIONS: ${violationsCount}`);
console.log('=====================================================================');

if (violationsCount > 0) {
  process.exit(1);
} else {
  console.log('ALL CATCH BLOCKS COMPLIANT WITH ZERO ERROR SWALLOWING & STRICT OFFLINE GATING.');
  process.exit(0);
}
