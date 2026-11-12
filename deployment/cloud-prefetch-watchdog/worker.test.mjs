import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { ensurePack, windowAt, digestStatus, githubClient, verifyGithubReadAccess } from './worker.mjs';

const token = 'unit-test-placeholder';
const now = new Date('2026-10-25T10:55:00Z'); // 12:55 Cyprus
const edition = '2026-10-25-midday';
const digest = (stamp = '2026-10-25T10:40:00Z', ready = true) =>
  `# Prepared synthesis digest · oracle-synthesis/1\nPrepared at ${stamp}; expires after 90 minutes.\nPrivate submission workflow installed: True\nsubmission_ready=${ready}.\n@Edition v=1 id=${edition} published=auto\n@Pack sha256=${'a'.repeat(64)}\n`;
const files = ['digest.md', 'research_pack.json'].map(name => ({ name, type: 'file', size: 100 }));
function mock(entries) {
  const calls = [];
  const fetcher = async (url, init) => {
    calls.push({ url, ...init });
    assert.equal(new URL(url).host, 'api.github.com');
    assert.equal(init.headers.Authorization, `Bearer ${token}`);
    assert.equal(init.redirect, 'manual');
    const next = entries.shift();
    assert.ok(next, 'Unexpected extra HTTP request');
    if (next.match) assert.match(url, next.match);
    return new Response(next.status === 204 ? null : JSON.stringify(next.value), { status: next.status || 200 });
  };
  return { fetcher, calls, entries };
}
const missing = { status: 404, value: {} };
const encoded = text => ({ encoding: 'base64', content: Buffer.from(text).toString('base64') });

function cronCovers(at) {
  const [minutes, hours] = JSON.parse(readFileSync(new URL('./wrangler.jsonc', import.meta.url), 'utf8')).triggers.crons[0].split(' ');
  assert.equal(minutes, '*/5');
  return at.getUTCMinutes()%5===0 && hours.split(',').some(range => {
    const [first,last] = range.split('-').map(Number);
    return first<=at.getUTCHours() && at.getUTCHours()<=last;
  });
}

test('all editions and UTC cron coverage survive the October DST transition', () => {
  for (const [date, offset] of [['2026-10-24', 3], ['2026-10-25', 2]]) {
    for (const [hour, slot] of [[7, 'morning'], [13, 'midday'], [19, 'evening']]) {
      const task = new Date(`${date}T${String(hour-offset).padStart(2,'0')}:30:00Z`);
      for (const lead of [70, 55, 40, 25, 15, 10, 5]) {
        const at = new Date(task.getTime() - lead * 60000);
        const window = windowAt(at);
        assert.equal(window.slot, slot);
        assert.equal(window.edition, `${date}-${slot}`);
        assert.equal(window.canDispatch, lead > 10);
        assert.equal(window.taskAt.toISOString(), task.toISOString());
        assert.ok(cronCovers(at));
        assert.equal(at.getUTCMinutes() % 5, 0);
      }
      assert.equal(windowAt(new Date(task.getTime()-71*60000)), null);
      assert.equal(windowAt(new Date(task.getTime()-4*60000)), null);
      for (const delay of [0, 25, 65, 120]) {
        const at = new Date(task.getTime()+delay*60000);
        assert.deepEqual(windowAt(at), { slot, edition: `${date}-${slot}`, taskAt: task, canDispatch: true, late: true });
        assert.ok(cronCovers(at));
      }
      assert.equal(windowAt(new Date(task.getTime()+121*60000)), null);
    }
  }
});

test('outside collection windows makes no HTTP calls and needs no credential', async () => {
  const result = await ensurePack({}, { now: new Date('2026-10-25T13:35:00Z'), fetcher: () => assert.fail('HTTP outside window') });
  assert.deepEqual(result, { status: 'outside_window', ai_calls: 0 });
});

test('only a complete, ready digest with life beyond synthesis is accepted', () => {
  const window = windowAt(now);
  assert.equal(digestStatus(digest(), window, now), 'ready');
  assert.equal(digestStatus(digest('2026-10-25T09:35:00Z'), window, now), 'stale'); // alive now, expires before AI
  assert.equal(digestStatus(digest('2026-10-25T10:56:00Z'), window, now), 'invalid_digest');
  assert.equal(digestStatus(digest(undefined, false), window, now), 'submission_unready');
  assert.equal(digestStatus(digest().replace(edition, '2026-10-25-evening'), window, now), 'invalid_digest');
});

test('an existing synthesis freezes the pack without any dispatch or collection', async () => {
  const api = mock([{ value: { type: 'file' } }]);
  const result = await ensurePack({ GITHUB_PREFETCH_TOKEN: token }, { now, fetcher: api.fetcher });
  assert.equal(result.status, 'already_submitted');
  assert.equal(api.calls.length, 1);
});

test('actual fresh committed files suppress collector dispatch', async () => {
  const api = mock([missing, { value: files }, { value: encoded(digest()) }]);
  const result = await ensurePack({ GITHUB_PREFETCH_TOKEN: token }, { now, fetcher: api.fetcher });
  assert.equal(result.status, 'ready');
  assert.ok(api.calls.every(call => !call.method));
});

test('a missing pack dispatches only the correct private Python workflow', async () => {
  const api = mock([missing, missing, { value: { workflow_runs: [] } }, { status: 204, match: /prepare-synthesis\.yml\/dispatches$/ }]);
  const result = await ensurePack({ GITHUB_PREFETCH_TOKEN: token }, { now, fetcher: api.fetcher });
  assert.equal(result.status, 'dispatch_accepted');
  assert.equal(result.previous_pack, 'missing');
  const writes = api.calls.filter(call => call.method === 'POST');
  assert.equal(writes.length, 1);
  assert.deepEqual(JSON.parse(writes[0].body), { ref: 'main', inputs: { slot: 'midday' } });
  assert.equal(result.ai_calls, 0);
});

test('recent queued/running collectors suppress duplicate dispatch', async () => {
  const api = mock([missing, missing, { value: { workflow_runs: [{ id: 123, status: 'queued', created_at: '2026-10-25T10:51:00Z' }] } }]);
  const result = await ensurePack({ GITHUB_PREFETCH_TOKEN: token }, { now, fetcher: api.fetcher });
  assert.equal(result.status, 'collector_in_flight');
  assert.equal(result.run_id, 123);
  assert.ok(api.calls.every(call => !call.method));
});

test('after the freeze, a missing pack raises an audit failure without dispatch', async () => {
  const api = mock([missing, missing]);
  await assert.rejects(ensurePack({ GITHUB_PREFETCH_TOKEN: token }, {
    now: new Date('2026-10-25T11:20:00Z'), fetcher: api.fetcher,
  }), /final pre-briefing audit/);
  assert.equal(api.calls.length, 2);
});

test('credential failures are reported without response bodies or token disclosure', async () => {
  const api = githubClient(token, async () => new Response('sensitive upstream detail', { status: 403 }));
  await assert.rejects(api('/actions/workflows/prepare-synthesis.yml/runs'), error => {
    assert.equal(error.message, 'GitHub GET failed: HTTP 403');
    assert.ok(!error.message.includes(token));
    return true;
  });
});

test('deployment credential diagnostic is strictly read-only', async () => {
  const api = mock([{ value: { type: 'file' } }, { value: { state: 'active' } }]);
  const result = await verifyGithubReadAccess({ GITHUB_PREFETCH_TOKEN: token }, api.fetcher);
  assert.equal(result.status, 'github_read_access_verified');
  assert.equal(result.collector_active, true);
  assert.equal(result.ai_calls, 0);
  assert.ok(api.calls.every(call => !call.method && !call.body));
});

test('deployment diagnostic rejects a disabled collector', async () => {
  const api = mock([{ value: { type: 'file' } }, { value: { state: 'disabled_manually' } }]);
  await assert.rejects(verifyGithubReadAccess({ GITHUB_PREFETCH_TOKEN: token }, api.fetcher), /not active/);
  assert.equal(api.calls.length, 2);
});

test('Cloudflare-compatible manual redirects never follow a credential-bearing request', async () => {
  let calls = 0;
  const api = githubClient(token, async (url, init) => {
    calls++;
    assert.equal(init.redirect, 'manual');
    return new Response('do not disclose this body', { status: 302, headers: { Location: 'https://other.example/' } });
  });
  await assert.rejects(api('/contents/README.md'), /GitHub GET failed: HTTP 302/);
  assert.equal(calls, 1);
});

test('the observed evening delay dispatches only the existing Python workflow for an expired pack', async () => {
  const now = new Date('2026-11-12T17:55:00Z'); // first tick after the 19:51 local expiry
  const old = digest('2026-11-12T16:21:23Z').replace(edition, '2026-11-12-evening');
  const api = mock([missing, { value: files }, { value: encoded(old) }, { value: { workflow_runs: [] } },
    { ...missing, match: /sources\/synthesis\/2026-11-12-evening\.md/ }, { status: 204, match: /prepare-synthesis\.yml\/dispatches$/ }]);
  const result = await ensurePack({ GITHUB_PREFETCH_TOKEN: token }, { now, fetcher: api.fetcher });
  assert.equal(result.status, 'dispatch_accepted');
  assert.equal(result.previous_pack, 'stale');
  assert.deepEqual(JSON.parse(api.calls.at(-1).body), { ref: 'main', inputs: { slot: 'evening' } });
  assert.equal(digestStatus(old, windowAt(new Date('2026-11-12T18:35:00Z')), new Date('2026-11-12T18:35:00Z')), 'stale');
});

test('late recovery leaves a still-valid pack alone even just before expiry', async () => {
  const now = new Date('2026-10-25T11:31:00Z');
  const api = mock([missing, { value: files }, { value: encoded(digest('2026-10-25T10:02:00Z')) }]);
  const result = await ensurePack({ GITHUB_PREFETCH_TOKEN: token }, { now, fetcher: api.fetcher });
  assert.equal(result.status, 'ready');
  assert.ok(api.calls.every(call => !call.method));
});

test('late recovery does not dispatch if a submission appears during the readiness check', async () => {
  const now = new Date('2026-10-25T12:35:00Z');
  const api = mock([missing, missing, { value: { workflow_runs: [] } }, { value: { type: 'file' } }]);
  const result = await ensurePack({ GITHUB_PREFETCH_TOKEN: token }, { now, fetcher: api.fetcher });
  assert.equal(result.status, 'already_submitted');
  assert.ok(api.calls.every(call => !call.method));
});
