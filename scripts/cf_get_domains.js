const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

try {
  const configPath = path.join(os.homedir(), '.wrangler', 'config', 'default.toml');
  const content = fs.readFileSync(configPath, 'utf8');
  const match = content.match(/oauth_token\s*=\s*\"([^\"]+)\"/);
  const token = match[1];
  const accountId = 'f646340e49818ac9843b366a6fed8106';
  const projectName = 'marketflow';

  const url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/pages/projects/${projectName}/domains`;
  const curlCmd = `curl.exe -s "${url}" -H "Authorization: Bearer ${token}"`;
  const output = execSync(curlCmd, { encoding: 'utf8', timeout: 15000 });
  console.log('Domains on project:', output);
} catch (err) {
  console.error('Error:', err.message);
}
