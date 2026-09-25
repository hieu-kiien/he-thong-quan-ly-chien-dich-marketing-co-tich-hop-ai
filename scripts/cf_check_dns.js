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

  // Check DNS records
  const dnsUrl = `https://api.cloudflare.com/client/v4/zones/${zoneId}/dns_records?name=marketing.kienhieu.id.vn`;
  const curlCmd = `curl.exe -s "${dnsUrl}" -H "Authorization: Bearer ${token}"`;
  const output = execSync(curlCmd, { encoding: 'utf8', timeout: 15000 });
  const data = JSON.parse(output);

  console.log('DNS records for marketing.kienhieu.id.vn:', data.result ? data.result.length : 0);
  if (data.result && data.result.length > 0) {
    console.log('Existing DNS record:', data.result[0].type, data.result[0].name, '->', data.result[0].content);
  } else {
    console.log('Adding CNAME record for marketing -> marketflow-7vt.pages.dev...');
    const createUrl = `https://api.cloudflare.com/client/v4/zones/${zoneId}/dns_records`;
    const payload = JSON.stringify({
      type: 'CNAME',
      name: 'marketing',
      content: 'marketflow-7vt.pages.dev',
      proxied: true,
      ttl: 1
    });
    const addCmd = `curl.exe -s -X POST "${createUrl}" -H "Authorization: Bearer ${token}" -H "Content-Type: application/json" -d "${payload.replace(/"/g, '\\"')}"`;
    const addRes = execSync(addCmd, { encoding: 'utf8', timeout: 15000 });
    console.log('Add DNS record response:', addRes);
  }
} catch (err) {
  console.error('Error:', err.message);
}
