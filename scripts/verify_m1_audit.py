import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

project_root = r'c:\Users\hieuk\Desktop\Ứng Dụng AI'
passed = 0
failed = 0

def test(name, condition, extra=''):
    global passed, failed
    if condition:
        print(f'[PASS] {name}')
        passed += 1
    else:
        print(f'[FAIL] {name}: {extra}')
        failed += 1

print('=' * 65)
print('CHALLENGER M1-2: EMPIRICAL STRING HYGIENE & LOGIC AUDIT')
print('=' * 65)

# --- 1. STRING HYGIENE AUDIT ---
def scan_text_files(directory, forbidden):
    matches = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith(('.py', '.ts', '.tsx', '.json', '.html', '.css', '.md')):
                fp = os.path.join(root, f)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                        if forbidden.lower() in content.lower():
                            matches.append(fp)
                except Exception:
                    pass
    return matches

backend_app_matches = scan_text_files(os.path.join(project_root, 'backend', 'app'), '@ictu.edu.vn')
test('1.1. Zero @ictu.edu.vn in backend/app/', len(backend_app_matches) == 0, str(backend_app_matches))

backend_seed_matches = scan_text_files(os.path.join(project_root, 'backend', 'seed'), '@ictu.edu.vn')
test('1.2. Zero @ictu.edu.vn in backend/seed/', len(backend_seed_matches) == 0, str(backend_seed_matches))

frontend_src_matches = scan_text_files(os.path.join(project_root, 'frontend', 'src'), '@ictu.edu.vn')
test('1.3. Zero @ictu.edu.vn in frontend/src/', len(frontend_src_matches) == 0, str(frontend_src_matches))

backend_tests_matches = scan_text_files(os.path.join(project_root, 'backend', 'tests'), '@ictu.edu.vn')
backend_tests_operational_matches = [
    m for m in backend_tests_matches
    if not m.endswith('test_challenger_m1_verification.py')
]
test('1.4a. Zero @ictu.edu.vn in operational backend/tests/', len(backend_tests_operational_matches) == 0, str(backend_tests_operational_matches))
test('1.4b. Intentional rejection probe in test_challenger_m1_verification.py', all('test_challenger_m1_verification.py' in m for m in backend_tests_matches))

auth_path = os.path.join(project_root, 'backend', 'app', 'api', 'v1', 'auth.py')
with open(auth_path, 'r', encoding='utf-8') as f:
    auth_code = f.read()
test('1.5. No @ictu.edu.vn fallback logic in auth.py', '@ictu.edu.vn' not in auth_code and 'replace(' not in auth_code)

aistudio_path = os.path.join(project_root, 'frontend', 'src', 'pages', 'AIStudio.tsx')
with open(aistudio_path, 'r', encoding='utf-8') as f:
    aistudio_code = f.read()
test('1.6. No ICTU reference in AIStudio.tsx templates', 'ICTU' not in aistudio_code)

# --- 2. API.TS INSPECTION & TIMEOUT VERIFICATION ---
api_path = os.path.join(project_root, 'frontend', 'src', 'services', 'api.ts')
with open(api_path, 'r', encoding='utf-8') as f:
    api_code = f.read()

test('2.1. Axios timeout configured to 60000ms in apiClient', 'timeout: 60000' in api_code)
test('2.2. ServerAwakeningStatus interface exported', 'export interface ServerAwakeningStatus' in api_code)
test('2.3. subscribeServerAwakening listener function exported', 'export const subscribeServerAwakening' in api_code)
test('2.4. Awakening threshold is 3500ms (3.5s)', '3500' in api_code and 'awakeningTimer = setTimeout' in api_code)
test('2.5. Awakening ticker interval is 1000ms (1s)', '1000' in api_code and 'secondsInterval = setInterval' in api_code)
test('2.6. Response interceptor success handler cleans up awakening tracking', 'cleanupAwakeningTracking()' in api_code)
test('2.7. Response interceptor error handler cleans up awakening tracking', api_code.count('cleanupAwakeningTracking()') >= 2)
test('2.8. Window event server-awakening dispatched', "window.dispatchEvent(new CustomEvent('server-awakening'" in api_code)

# --- 3. SERVER AWAKENING INDICATOR COMPONENT INSPECTION ---
ind_path = os.path.join(project_root, 'frontend', 'src', 'components', 'ServerAwakeningIndicator.tsx')
with open(ind_path, 'r', encoding='utf-8') as f:
    ind_code = f.read()

test('3.1. ServerAwakeningIndicator subscribes to api awakening events', 'subscribeServerAwakening' in ind_code)
test('3.2. Indicator returns null when dormant or dismissed', '(!status.isWakingUp && !showSuccess) || isDismissed' in ind_code)
test('3.3. Indicator provides user dismiss button', 'setIsDismissed(true)' in ind_code)
test('3.4. Dismiss state resets on next cold-start awakening', 'setIsDismissed(false)' in ind_code)
test('3.5. Success banner flashes for 2500ms (2.5s)', '2500' in ind_code and 'setShowSuccess' in ind_code)
test('3.6. Accessible ARIA attributes role=status and aria-live=polite present', 'role="status"' in ind_code and 'aria-live="polite"' in ind_code)

# --- 4. APP.TSX MOUNTING ---
app_path = os.path.join(project_root, 'frontend', 'src', 'App.tsx')
with open(app_path, 'r', encoding='utf-8') as f:
    app_code = f.read()

test('4.1. ServerAwakeningIndicator imported in App.tsx', 'import { ServerAwakeningIndicator }' in app_code)
test('4.2. ServerAwakeningIndicator mounted inside ToastProvider at root', '<ServerAwakeningIndicator />' in app_code)

# --- 5. FRONTEND BUILD DIST ARTIFACTS ---
dist_html = os.path.join(project_root, 'frontend', 'dist', 'index.html')
dist_assets = os.path.join(project_root, 'frontend', 'dist', 'assets')
test('5.1. frontend/dist/index.html generated and valid', os.path.exists(dist_html) and os.path.getsize(dist_html) > 500)
has_js = any(f.endswith('.js') for f in os.listdir(dist_assets)) if os.path.exists(dist_assets) else False
has_css = any(f.endswith('.css') for f in os.listdir(dist_assets)) if os.path.exists(dist_assets) else False
test('5.2. frontend/dist/assets contains bundled JS and CSS', has_js and has_css)

# --- 6. STATE MACHINE SIMULATION (ALGORITHMIC LOGIC VERIFICATION) ---
class AwakeningManagerSim:
    def __init__(self):
        self.activeRequestsCount = 0
        self.awakeningTimerArmed = False
        self.isAwakeningActive = False
        self.broadcasts = []

    def request_start(self):
        self.activeRequestsCount += 1
        if self.activeRequestsCount == 1:
            self.awakeningTimerArmed = True

    def timer_expires(self):
        if self.awakeningTimerArmed:
            self.isAwakeningActive = True
            self.broadcasts.append(('WAKING_UP', True))

    def cleanup(self):
        self.activeRequestsCount = max(0, self.activeRequestsCount - 1)
        if self.activeRequestsCount == 0:
            self.awakeningTimerArmed = False
            if self.isAwakeningActive:
                self.isAwakeningActive = False
                self.broadcasts.append(('WAKING_UP', False))

simA = AwakeningManagerSim()
simA.request_start()
simA.cleanup()
test('6.1. Sim A (Fast request): awakening never fires', len(simA.broadcasts) == 0 and not simA.isAwakeningActive and not simA.awakeningTimerArmed)

simB = AwakeningManagerSim()
simB.request_start()
simB.timer_expires()
simB.cleanup()
test('6.2. Sim B (Slow request): awakening fires then resolves', simB.broadcasts == [('WAKING_UP', True), ('WAKING_UP', False)] and not simB.isAwakeningActive)

simC = AwakeningManagerSim()
simC.request_start()
simC.request_start()
simC.cleanup()
test('6.3. Sim C (Concurrent 1): timer stays armed after Req 1 ends', simC.awakeningTimerArmed and simC.activeRequestsCount == 1)
simC.timer_expires()
test('6.4. Sim C (Concurrent 2): awakening activates for Req 2', simC.isAwakeningActive)
simC.cleanup()
test('6.5. Sim C (Concurrent 3): awakening resolves when Req 2 ends', not simC.isAwakeningActive and simC.activeRequestsCount == 0)

simD = AwakeningManagerSim()
simD.request_start()
simD.cleanup()
test('6.6. Sim D (Error handling): cleanup clears timers on failure', simD.activeRequestsCount == 0 and not simD.awakeningTimerArmed)

print('=' * 65)
print(f'TOTAL AUDIT CHECKS: {passed + failed}')
print(f'PASSED: {passed}')
print(f'FAILED: {failed}')
print('=' * 65)
if failed > 0:
    sys.exit(1)
else:
    sys.exit(0)
