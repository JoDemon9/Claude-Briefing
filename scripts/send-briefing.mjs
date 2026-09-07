import fs from 'node:fs/promises';

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT  = process.env.TELEGRAM_CHAT_ID;
const BASE  = process.env.BRIEFING_BASE_URL || 'https://jodemon9.github.io/oracle-briefing';
const date  = process.argv[2] ?? new Date().toISOString().slice(0, 10);

if (!TOKEN || !CHAT) throw new Error('Λείπουν TELEGRAM_BOT_TOKEN ή TELEGRAM_CHAT_ID');

// Support both docs/briefings/YYYY-MM-DD.md and briefings/oracle-briefing-YYYY-MM-DD.md
let mdPath = `docs/briefings/${date}.md`;
try {
  await fs.access(mdPath);
} catch {
  mdPath = `briefings/oracle-briefing-${date}.md`;
}

const md = await fs.readFile(mdPath, 'utf8');

// --- εξαγωγή των βασικών από το markdown ---
const grab = (start, end) => {
  const i = md.indexOf(start);
  if (i === -1) return '';
  const j = end ? md.indexOf(end, i) : md.length;
  return md.slice(i, j === -1 ? md.length : j);
};
const firstHeading = (block) => (block.match(/^###?\s+(.+)$/m) ?? [, ''])[1].trim();

const topStory = firstHeading(grab('## ⭐', '## 📊'));
const dashRows = grab('## 📊', '## 🏦')
  .split('\n').filter(l => l.startsWith('| **')).slice(0, 6)
  .map(l => {
    const c = l.split('|').map(s => s.trim()).filter(Boolean);
    return `• ${c[0].replace(/\*\*/g, '')}: ${c[1]} (${c[2]})`;
  }).join('\n');
const myFile = grab('## 🎯', '## 📅')
  .split('\n').filter(l => l.startsWith('*   **')).slice(0, 2)
  .map(l => '• ' + l.replace(/^\*\s+\*\*/, '').replace(/\*\*/g, '').split(':')[0]).join('\n');
const deadlines = grab('## 📅', '## 🔍')
  .split('\n').filter(l => l.startsWith('*   **')).slice(0, 3)
  .map(l => '• ' + l.replace(/^\*\s+\*\*/, '').replace(/\*\*/g, '').replace(/\(\[.*?\]\(.*?\)\)/g, '').trim()).join('\n');

const esc = (s) => s.replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

let text =
`🏛️ <b>THE ORACLE SOVEREIGN</b> — ${date}

⭐ <b>Θέμα της ημέρας</b>
${esc(topStory)}

📊 <b>Αγορές</b>
${esc(dashRows)}

🎯 <b>Ο φάκελός μου</b>
${esc(myFile) || '—'}

📅 <b>Προθεσμίες</b>
${esc(deadlines) || '—'}

📖 <a href="${BASE}/briefings/${date}.html">Πλήρης έκδοση</a>`;

if (text.length > 4000) text = text.slice(0, 3900) + '\n…\n' + `<a href="${BASE}/briefings/${date}.html">Πλήρης έκδοση</a>`;

const api = (method, body) =>
  fetch(`https://api.telegram.org/bot${TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(async r => {
    const j = await r.json();
    if (!j.ok) throw new Error(`${method}: ${j.description}`);
    return j;
  });

await api('sendMessage', {
  chat_id: CHAT,
  text,
  parse_mode: 'HTML',
  link_preview_options: { is_disabled: true },
  disable_notification: false
});

console.log('Στάλθηκε το briefing', date);
