'use strict';
async function getJSON(url) {
  const response = await fetch(url, {cache: 'no-store', signal: AbortSignal.timeout(10000)});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
for (const button of document.querySelectorAll('.copy-note')) {
  button.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(button.previousElementSibling.textContent); button.textContent = 'Copied'; }
    catch { button.textContent = 'Select and copy the Note above'; }
  });
}
for (const a of document.querySelectorAll('[data-verify-download]')) {
  a.addEventListener('click', async event => {
    if (!globalThis.crypto?.subtle) return; // Native download remains usable without JS/secure context.
    event.preventDefault();
    const status = a.closest('section').querySelector('.download-status');
    status.textContent = 'Downloading and checking SHA-256…';
    try {
      const response = await fetch(a.href, {signal: AbortSignal.timeout(60000)});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const bytes = await response.arrayBuffer();
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      const hash = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, '0')).join('');
      if (hash !== a.dataset.sha) throw new Error('SHA-256 mismatch. Download blocked; reload or check the manifest.');
      const url = URL.createObjectURL(new Blob([bytes], {type:'image/tiff'}));
      const download = document.createElement('a'); download.href = url;
      download.download = new URL(a.href).pathname.split('/').pop();
      document.body.append(download); download.click(); download.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      status.textContent = 'SHA-256 matches the validated artifact. Saved with its unique filename.';
    } catch (error) { status.textContent = `Download failed: ${error.message}`; }
  });
}
async function updateFeed() {
  const status = document.getElementById('feed-status');
  if (!status) return;
  let feed, channel;
  try {
    const release = await getJSON('https://api.github.com/repos/buffedlizard55-lab/7GEMSDOE/releases/tags/research-feed');
    feed = JSON.parse(release.body); channel = 'Daily release feed';
    if (!Array.isArray(feed.rows) || !feed.rows.length) throw new Error('Missing rows');
  } catch {
    try { feed = await getJSON('knowledge/feed.json'); channel = 'Bundled fallback (live refresh unavailable)'; }
    catch { status.textContent += ' Live and bundled fetch failed; the table below is a dated static snapshot.'; return; }
  }
  const ageHours = (Date.now() - Date.parse(feed.verified_utc))/3600000;
  const stale = !Number.isFinite(ageHours) || ageHours > 36 || ageHours < -1;
  const sourceFailures = (feed.source_checks || []).filter(r => r.status !== 'excerpt_found').length;
  status.textContent = `${channel}. ${stale ? 'STALE — ' : ''}Verified: ${feed.verified_utc || 'unknown'}. Last attempt: ${feed.status}. ${sourceFailures} source checks need review.`;
  const table = document.createElement('table');
  const head = table.createTHead().insertRow();
  for (const title of ['Participant','Public best','Rank at snapshot']) { const th=document.createElement('th'); th.textContent=title; head.append(th); }
  const body = table.createTBody();
  const wanted = new Set(['extradr19','smashi34','smrtdoog5','SDCF9','wbg1']);
  for (const row of feed.rows.filter(r => r.rank <= 2 || wanted.has(r.participant))) {
    const tr = body.insertRow();
    for (const value of [row.participant, Number(row.score).toFixed(4), row.rank]) tr.insertCell().textContent = value;
  }
  document.getElementById('feed-rows').replaceChildren(table);
}
updateFeed();
