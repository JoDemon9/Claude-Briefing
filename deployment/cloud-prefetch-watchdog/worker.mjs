// Independent cloud timer. This Worker never invokes AI or gathers briefing data.
// Its only write is dispatching the existing private Python collector workflow.
const REPO = 'JoDemon9/Claude-Briefing-Private';
const WORKFLOW = 'prepare-synthesis.yml';
const ZONE = 'Asia/Nicosia';
const FORMAT = new Intl.DateTimeFormat('en-CA', {
  timeZone: ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
});
const EDITIONS = [[7, 'morning'], [13, 'midday'], [19, 'evening']];

export function windowAt(now) {
  const parts = Object.fromEntries(FORMAT.formatToParts(now).map(x => [x.type, x.value]));
  const seconds = Number(parts.hour) * 3600 + Number(parts.minute) * 60 + Number(parts.second);
  for (const [hour, slot] of EDITIONS) {
    const lead = (hour * 3600 + 30 * 60 - seconds) * 1000;
    // Freeze ten minutes before the AI; allow an audit five minutes before it.
    if (lead <= 70 * 60000 && lead >= 5 * 60000) {
      return { slot, edition: `${parts.year}-${parts.month}-${parts.day}-${slot}`,
        taskAt: new Date(now.getTime() + lead), canDispatch: lead > 10 * 60000 };
    }
  }
  return null;
}

export function digestStatus(text, window, now) {
  const prepared = /^Prepared at (\S+); expires after 90 minutes\./m.exec(text);
  const edition = /^@Edition v=1 id=([^\s]+)/m.exec(text);
  const sha = /^@Pack sha256=([0-9a-f]{64})$/m.exec(text);
  if (!text.startsWith('# Prepared synthesis digest · oracle-synthesis/1\n') ||
      !prepared || edition?.[1] !== window.edition || !sha) return 'invalid_digest';
  const stamp = Date.parse(prepared[1]);
  const age = now.getTime() - stamp;
  if (!Number.isFinite(stamp) || age < 0) return 'invalid_digest';
  if (age > 90 * 60000 || window.taskAt.getTime() + 20 * 60000 > stamp + 90 * 60000) return 'stale';
  if (!/^submission_ready=true\./m.test(text) ||
      !/^Private submission workflow installed: True$/m.test(text)) return 'submission_unready';
  return 'ready';
}

export function githubClient(token, fetcher = fetch) {
  if (!token) throw new Error('GITHUB_PREFETCH_TOKEN is not configured');
  return async (path, options = {}) => {
    const response = await fetcher(`https://api.github.com/repos/${REPO}${path}`, {
      ...options, redirect: 'error', signal: AbortSignal.timeout(12000),
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Oracle-cloud-prefetch-watchdog',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
    });
    if (response.status === 404 && options.allowMissing) return null;
    if (!response.ok) throw new Error(`GitHub ${options.method || 'GET'} failed: HTTP ${response.status}`);
    if (response.status === 204) return { accepted: true };
    return response.json();
  };
}

export async function ensurePack(env, { now = new Date(), fetcher = fetch } = {}) {
  const window = windowAt(now);
  if (!window) return { status: 'outside_window', ai_calls: 0 };
  const api = githubClient(env.GITHUB_PREFETCH_TOKEN, fetcher);
  const context = { edition: window.edition, checked_at: now.toISOString(), ai_calls: 0 };
  // An authored submission freezes its pack, including a manual early run.
  const submission = await api(`/contents/sources/synthesis/${window.edition}.md?ref=main`, { allowMissing: true });
  if (submission?.type === 'file') return { ...context, status: 'already_submitted' };
  const files = await api(`/contents/research/runs/${window.edition}?ref=main`, { allowMissing: true });
  const complete = Array.isArray(files) && ['digest.md', 'research_pack.json'].every(name =>
    files.some(file => file.name === name && file.type === 'file' && file.size > 0));
  let status = 'missing';
  if (complete) {
    const file = await api(`/contents/research/runs/${window.edition}/digest.md?ref=main`);
    if (file?.encoding !== 'base64' || !file.content) throw new Error('Unexpected GitHub digest encoding');
    const bytes = Uint8Array.from(atob(file.content.replace(/\s/g, '')), ch => ch.charCodeAt(0));
    status = digestStatus(new TextDecoder().decode(bytes), window, now);
    if (status === 'ready') return { ...context, status };
    // A collector retry cannot fix submission credentials or malformed outputs.
    if (['submission_unready', 'invalid_digest'].includes(status)) throw new Error(`Pack ${status}: ${window.edition}`);
  }
  if (!window.canDispatch) throw new Error(`Pack ${status} at final pre-briefing audit: ${window.edition}`);
  const runs = await api(`/actions/workflows/${WORKFLOW}/runs?branch=main&per_page=10`);
  const active = runs.workflow_runs?.find(run => ['queued', 'in_progress', 'pending', 'waiting', 'requested'].includes(run.status)
    && now.getTime() - Date.parse(run.created_at) >= 0
    && now.getTime() - Date.parse(run.created_at) < 10 * 60000);
  if (active) return { ...context, status: 'collector_in_flight', run_id: active.id };
  await api(`/actions/workflows/${WORKFLOW}/dispatches`, {
    method: 'POST', body: JSON.stringify({ ref: 'main', inputs: { slot: window.slot } }),
  });
  // Accepted is not ready. A subsequent tick must observe the committed output.
  return { ...context, status: 'dispatch_accepted', previous_pack: status };
}

export async function verifyGithubReadAccess(env, fetcher = fetch) {
  const api = githubClient(env.GITHUB_PREFETCH_TOKEN, fetcher);
  // Deployment diagnostic only: never dispatch or collect outside a due window.
  await api('/contents/README.md?ref=main');
  const workflow = await api(`/actions/workflows/${WORKFLOW}`);
  if (workflow.state !== 'active') throw new Error('Private collector workflow is not active');
  return { status: 'github_read_access_verified', collector_active: true, ai_calls: 0 };
}

export default {
  async scheduled(_controller, env) {
    // Use the real clock, never a delayed event's nominal timestamp.
    let result = await ensurePack(env);
    if (result.status === 'outside_window' && env.VERIFY_GITHUB_ACCESS === 'true') {
      result = await verifyGithubReadAccess(env);
    }
    console.log(JSON.stringify(result));
    return result;
  },
  fetch() { return new Response('Not found', { status: 404 }); },
};
