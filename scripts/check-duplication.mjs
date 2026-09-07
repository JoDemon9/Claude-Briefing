import fs from 'node:fs/promises';

const html = await fs.readFile(process.argv[2] ?? 'docs/index.html', 'utf8');
const strip = (s) => s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();

// ζεύγη: το ορατό κείμενο της κάρτας και το κείμενο του details της
const cards = html.split('<article').slice(1);
const problems = [];

cards.forEach((card, i) => {
  const det = card.match(/<details[\s\S]*?<\/details>/);
  if (!det) return;
  const hidden = strip(det[0]);
  const visible = strip(card.replace(det[0], ''));
  const hidWords = new Set(hidden.split(' ').filter(w => w.length > 4));
  if (!hidWords.size) return;
  let shared = 0;
  for (const w of hidWords) if (visible.includes(w)) shared++;
  const overlap = shared / hidWords.size;
  if (overlap > 0.5) problems.push(Κάρτα #: επικάλυψη %);
});

if (problems.length) {
  console.error('Το αναπτυσσόμενο μπλοκ επαναλαμβάνει το ορατό κείμενο:\n' + problems.join('\n'));
  process.exit(1);
}
console.log('Έλεγχος επανάληψης: καθαρό.');
