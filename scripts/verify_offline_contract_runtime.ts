import axios from 'axios';

// 1. Mock in-memory localStorage
const mockStorage: Record<string, string> = {};
let storageWriteCount = 0;

(globalThis as any).localStorage = {
  getItem: (k: string) => mockStorage[k] || null,
  setItem: (k: string, v: string) => {
    storageWriteCount++;
    mockStorage[k] = String(v);
  },
  removeItem: (k: string) => { delete mockStorage[k]; },
  clear: () => {
    storageWriteCount = 0;
    for (const k in mockStorage) delete mockStorage[k];
  }
};

// 2. Intercept console.warn to count [OFFLINE DEMO] warnings
let demoWarnCount = 0;
const originalWarn = console.warn;
console.warn = (...args: any[]) => {
  const msg = args.join(' ');
  if (msg.includes('[OFFLINE DEMO]')) {
    demoWarnCount++;
  }
  originalWarn(...args);
};

// 3. Configure Axios default adapter to simulate network failure (ECONNREFUSED / !response)
axios.defaults.adapter = async (config) => {
  const err: any = new Error('Network Error: Simulated connection refused (127.0.0.1:8000 unreachable)');
  err.code = 'ECONNREFUSED';
  err.isAxiosError = true;
  err.config = config;
  err.response = undefined; // No response from server
  throw err;
};

async function run() {
  const {
    isOfflineDemoEnabled,
    authApi,
    workspaceApi,
    brandKitApi,
    campaignApi,
    productApi,
    contentApi,
    aiApi,
    analyticsApi,
    scheduleApi,
    settingsApi
  } = await import('../frontend/src/services/api');

  const demoEnabled = isOfflineDemoEnabled();
  console.log('=====================================================================');
  console.log(` RUNTIME OFFLINE CONTRACT TEST | Mode: VITE_ENABLE_OFFLINE_DEMO=${demoEnabled}`);
  console.log('=====================================================================');

  const testCases: { domain: string; name: string; invoke: () => Promise<any> }[] = [
    // 1. authApi
    { domain: 'authApi', name: 'login', invoke: () => authApi.login('marketer@ictu.edu.vn', 'secret') },
    
    // 2. workspaceApi
    { domain: 'workspaceApi', name: 'getAll', invoke: () => workspaceApi.getAll() },
    { domain: 'workspaceApi', name: 'getById', invoke: () => workspaceApi.getById(1) },
    { domain: 'workspaceApi', name: 'create', invoke: () => workspaceApi.create({ name: 'New WS', industry: 'Tech' } as any) },

    // 3. brandKitApi
    { domain: 'brandKitApi', name: 'getByWorkspace', invoke: () => brandKitApi.getByWorkspace(1) },
    { domain: 'brandKitApi', name: 'update', invoke: () => brandKitApi.update(1, { tone_of_voice: 'Professional' } as any) },

    // 4. campaignApi
    { domain: 'campaignApi', name: 'getAll', invoke: () => campaignApi.getAll() },
    { domain: 'campaignApi', name: 'getById', invoke: () => campaignApi.getById(1) },
    { domain: 'campaignApi', name: 'getKpi', invoke: () => campaignApi.getKpi(1) },
    { domain: 'campaignApi', name: 'getAIDoctor', invoke: () => campaignApi.getAIDoctor(1) },
    { domain: 'campaignApi', name: 'getAttribution', invoke: () => campaignApi.getAttribution(1) },

    // 5. productApi
    { domain: 'productApi', name: 'getAll', invoke: () => productApi.getAll() },

    // 6. contentApi
    { domain: 'contentApi', name: 'getAll', invoke: () => contentApi.getAll() },
    { domain: 'contentApi', name: 'approve', invoke: () => contentApi.approve(1) },
    { domain: 'contentApi', name: 'reject', invoke: () => contentApi.reject(1, 'Needs revisions') },
    { domain: 'contentApi', name: 'publish', invoke: () => contentApi.publish(1) },

    // 7. aiApi
    { domain: 'aiApi', name: 'generateIdeas', invoke: () => aiApi.generateIdeas('AI Marketing', 'facebook', 'Professional') },
    { domain: 'aiApi', name: 'generateDraft', invoke: () => aiApi.generateDraft('AI Launch', 'facebook', 'Marketers', 'Fast and smart', 'Professional') },
    { domain: 'aiApi', name: 'generateSummary', invoke: () => aiApi.generateSummary('Sample marketing draft text') },

    // 8. analyticsApi
    { domain: 'analyticsApi', name: 'getDashboard', invoke: () => analyticsApi.getDashboard() },

    // 9. scheduleApi
    { domain: 'scheduleApi', name: 'getAll', invoke: () => scheduleApi.getAll() },

    // 10. settingsApi
    { domain: 'settingsApi', name: 'testConnection', invoke: () => settingsApi.testConnection({ provider: 'gemini', api_key: 'test-key' }) },
    { domain: 'settingsApi', name: 'getKeys', invoke: () => settingsApi.getKeys() },
    { domain: 'settingsApi', name: 'getKeysList', invoke: () => settingsApi.getKeysList() }
  ];

  let passedCount = 0;
  let failedCount = 0;
  const results: { test: string; status: 'PASS' | 'FAIL'; note: string }[] = [];

  for (const tc of testCases) {
    const testId = `${tc.domain}.${tc.name}`;
    const initialWriteCount = storageWriteCount;

    if (!demoEnabled) {
      // MODE: PRODUCTION / DEMO DISABLED
      // EXPECTATION: MUST RE-THROW ERROR, ZERO LOCALSTORAGE WRITES, ZERO DEMO WARNINGS
      try {
        const res = await tc.invoke();
        failedCount++;
        results.push({
          test: testId,
          status: 'FAIL',
          note: `Swallowed network error and returned mock data: ${JSON.stringify(res)?.slice(0, 50)}...`
        });
        console.log(`[-] ${testId}: FAIL (Unexpected resolution when offline demo disabled)`);
      } catch (err: any) {
        const writesOccurred = storageWriteCount - initialWriteCount;
        if (writesOccurred > 0) {
          failedCount++;
          results.push({
            test: testId,
            status: 'FAIL',
            note: `Re-threw error but mutated localStorage (${writesOccurred} writes)!`
          });
          console.log(`[-] ${testId}: FAIL (Mutated localStorage before throwing!)`);
        } else if (err.code === 'ECONNREFUSED' || err.message?.includes('Network Error') || err.message?.includes('Simulated')) {
          passedCount++;
          results.push({
            test: testId,
            status: 'PASS',
            note: 'Re-threw network error faithfully without localStorage mutation'
          });
          console.log(`[+] ${testId}: PASS (Re-threw network error faithfully, 0 localStorage writes)`);
        } else {
          failedCount++;
          results.push({
            test: testId,
            status: 'FAIL',
            note: `Threw unexpected error: ${err.message}`
          });
          console.log(`[-] ${testId}: FAIL (Threw unexpected error: ${err.message})`);
        }
      }
    } else {
      // MODE: DEMO ENABLED
      // EXPECTATION: MUST RESOLVE WITH MOCK DATA, TRIGGER CONSOLE.WARN [OFFLINE DEMO]
      const initialWarnCount = demoWarnCount;
      try {
        const res = await tc.invoke();
        const warnTriggered = demoWarnCount > initialWarnCount;
        if (res !== undefined && warnTriggered) {
          passedCount++;
          results.push({
            test: testId,
            status: 'PASS',
            note: `Activated offline fallback with warning and returned mock data`
          });
          console.log(`[+] ${testId}: PASS (Offline fallback activated with warning)`);
        } else if (!warnTriggered) {
          failedCount++;
          results.push({
            test: testId,
            status: 'FAIL',
            note: 'Resolved but failed to log [OFFLINE DEMO] console.warn'
          });
          console.log(`[-] ${testId}: FAIL (Missing [OFFLINE DEMO] warning)`);
        } else {
          failedCount++;
          results.push({
            test: testId,
            status: 'FAIL',
            note: 'Resolved with undefined data'
          });
          console.log(`[-] ${testId}: FAIL (Resolved with undefined data)`);
        }
      } catch (err: any) {
        failedCount++;
        results.push({
          test: testId,
          status: 'FAIL',
          note: `Threw error instead of using offline fallback: ${err.message}`
        });
        console.log(`[-] ${testId}: FAIL (Threw error when demo fallback was expected: ${err.message})`);
      }
    }
  }

  console.log('\n=====================================================================');
  console.log(`TEST RESULTS SUMMARY (Mode: ${demoEnabled ? 'DEMO_ENABLED' : 'STANDARD_PRODUCTION'}):`);
  console.log(`Total Invocations: ${testCases.length}`);
  console.log(`Passed: ${passedCount}`);
  console.log(`Failed: ${failedCount}`);
  console.log(`Total LocalStorage Writes: ${storageWriteCount}`);
  console.log(`Total Demo Warnings: ${demoWarnCount}`);
  console.log('=====================================================================');

  if (failedCount > 0) {
    process.exit(1);
  } else {
    process.exit(0);
  }
}

run().catch((e) => {
  console.error('Test execution crashed:', e);
  process.exit(1);
});
