const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

try {
  const configPath = path.join(os.homedir(), '.wrangler', 'config', 'default.toml');
  const content = fs.readFileSync(configPath, 'utf8');
  const match = content.match(/oauth_token\s*=\s*\"([^\"]+)\"/);
  const token = match[1];
  const zoneId = '46dacfca94df32f628b04d77515620d7';

  const url = `https://api.cloudflare.com/client/v4/zones/${zoneId}/dns_records`;
  const curlCmd = `curl.exe -s "${url}" -H "Authorization: Bearer ${token}"`;
  const output = execSync(curlCmd, { encoding: 'utf8', timeout: 15000 });
  const data = JSON.parse(output);
  console.log('Success:', data.success);
  if (data.result) {
    console.log(`Found ${data.result.length} DNS records:`);
    data.result.forEach(r => console.log(`- ${r.type} ${r.name} -> ${r.content} (proxied: ${r.proxied})`));
  } else {
    console.log('Errors:', data.errors);
  }
} catch (err) {
  console.error('Error:', err.message);
}
