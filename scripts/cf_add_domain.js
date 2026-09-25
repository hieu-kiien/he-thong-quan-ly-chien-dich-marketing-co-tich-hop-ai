const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

try {
  const configPath = path.join(os.homedir(), '.wrangler', 'config', 'default.toml');
  const content = fs.readFileSync(configPath, 'utf8');
  const match = content.match(/oauth_token\s*=\s*\"([^\"]+)\"/);
  if (!match) {
    console.log('No token found in default.toml');
    process.exit(1);
  }
  const token = match[1];
  const accountId = 'f646340e49818ac9843b366a6fed8106';
  const projectName = 'marketflow';
  const domainName = 'marketing.kienhieu.id.vn';

  console.log(`Adding domain ${domainName} to Pages project ${projectName}...`);

  const url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/pages/projects/${projectName}/domains`;
  
  // Use curl.exe which is fast and reliable
  const payload = JSON.stringify({ name: domainName });
  const curlCmd = `curl.exe -s -X POST "${url}" -H "Authorization: Bearer ${token}" -H "Content-Type: application/json" -d "${payload.replace(/"/g, '\\"')}"`;
  
  const output = execSync(curlCmd, { encoding: 'utf8', timeout: 15000 });
  console.log('Response:', output);
} catch (err) {
  console.error('Error adding domain:', err.message);
  if (err.stdout) console.log('Stdout:', err.stdout);
}
