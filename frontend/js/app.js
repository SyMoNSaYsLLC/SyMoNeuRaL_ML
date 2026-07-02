const $ = id => document.getElementById(id);
let tab = 'manager';
let pollTimers = new Map();

const meta = {
  manager: ['Writer Manager', 'Ask here first. The manager routes code/image work and frees the GPU for the worker.'],
  image: ['Image Request', 'Image prompts still go through the Writer Manager, then Stable Diffusion gets the GPU exclusively.'],
  jobs: ['Handoff Jobs', 'Code/image artifacts returned by exclusive GPU worker handoff.'],
  ops: ['Ops / VRAM', 'Health, active engine, VRAM, and API checks.']
};

function add(role, txt, cls='') {
  const d = document.createElement('div');
  d.className = `msg ${role} ${cls}`.trim();
  d.innerHTML = `<span class="role">${role}</span>`;
  const body = document.createElement('div');
  body.textContent = txt;
  d.appendChild(body);
  $('messages').appendChild(d);
  $('messages').scrollTop = $('messages').scrollHeight;
  return body;
}

function addHtml(role, html, cls='') {
  const d = document.createElement('div');
  d.className = `msg ${role} ${cls}`.trim();
  d.innerHTML = `<span class="role">${role}</span><div>${html}</div>`;
  $('messages').appendChild(d);
  $('messages').scrollTop = $('messages').scrollHeight;
  return d;
}

function setTab(t) {
  tab = t;
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === t));
  $('title').textContent = meta[t][0];
  $('subtitle').textContent = meta[t][1];
  $('imageControls').classList.toggle('hide', t !== 'image');
  $('managerControls').classList.toggle('hide', t === 'jobs' || t === 'ops');
  $('jobsControls').classList.toggle('hide', t !== 'jobs');
  $('promptWrap').classList.toggle('hide', t === 'jobs');
  $('send').classList.toggle('hide', t === 'jobs');
  $('prompt').placeholder = t === 'ops' ? 'Try: vram, catalog, jobs' : (t === 'image' ? 'Describe the image you want...' : 'Type to the Writer Manager...');
  $('send').textContent = t === 'image' ? 'Submit Image Handoff' : 'Submit to Manager';
  if (t === 'jobs') refreshJobs();
}

document.querySelectorAll('.tab').forEach(b => b.onclick = () => setTab(b.dataset.tab));
$('clear').onclick = () => { $('messages').innerHTML = ''; $('debug').textContent = ''; };
$('refresh').onclick = () => { health(); if (tab === 'jobs') refreshJobs(); };
$('refreshJobs').onclick = refreshJobs;

document.querySelectorAll('[data-preset]').forEach(b => b.onclick = () => {
  const p = {fast:[512,512,22], quality:[512,512,34], landscape:[704,512,34], portrait:[512,704,34]}[b.dataset.preset];
  $('width').value = p[0]; $('height').value = p[1]; $('steps').value = p[2];
});

async function health() {
  try {
    const r = await fetch('/api/v1/health', {cache:'no-store'});
    const j = await r.json();
    $('status').textContent = JSON.stringify(j.engines, null, 2) + '\n' + JSON.stringify(j.vram.summary, null, 2);
  } catch(e) {
    $('status').textContent = e.message;
  }
}

$('send').onclick = async () => {
  const prompt = $('prompt').value.trim();
  if (!prompt && tab !== 'ops') return;
  if (tab === 'ops') return ops(prompt);
  return submitHandoff(prompt, tab === 'image' ? 'image' : null);
};

function imageOptions() {
  return {
    width: +$('width').value,
    height: +$('height').value,
    steps: +$('steps').value,
    cfg_scale: +$('cfg').value,
    seed: +$('seed').value,
    style: $('style').value,
    negative_prompt: $('negative').value,
    compat: $('compat').checked,
  };
}

async function submitHandoff(prompt, route=null) {
  add('user', prompt);
  const pending = add('assistant', 'Writer Manager is evaluating the request and routing it...');
  const payload = { prompt, route, ...imageOptions() };
  try {
    const r = await fetch('/api/v1/manager/submit', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const job = await r.json();
    if (!r.ok) {
      pending.textContent = JSON.stringify(job, null, 2);
      return;
    }
    pending.textContent = job.message || 'Handoff job started.';
    addJobCard(job);
    pollJob(job.id);
  } catch (e) {
    pending.textContent = e.message;
  }
}

function addJobCard(job) {
  const html = `
    <b>Job:</b> ${escapeHtml(job.id)}<br>
    <b>Status:</b> <span id="job-status-${job.id}">${escapeHtml(job.status)}</span><br>
    <b>Route:</b> <span id="job-kind-${job.id}">${escapeHtml(job.kind || 'routing')}</span><br>
    <b>Message:</b> <span id="job-msg-${job.id}">${escapeHtml(job.result_text || job.user_message || '')}</span>
    <div id="job-result-${job.id}"></div>
  `;
  addHtml('system', html, 'job');
}

async function pollJob(id) {
  if (pollTimers.has(id)) clearTimeout(pollTimers.get(id));
  const tick = async () => {
    try {
      const r = await fetch(`/api/v1/manager/jobs/${id}?include_image=true`, {cache:'no-store'});
      const job = await r.json();
      updateJobCard(job);
      health();
      if (!['done','failed','needs-review'].includes(job.status)) {
        pollTimers.set(id, setTimeout(tick, 2500));
      }
    } catch (e) {
      console.error(e);
      pollTimers.set(id, setTimeout(tick, 4000));
    }
  };
  tick();
}

function updateJobCard(job) {
  const st = document.getElementById(`job-status-${job.id}`);
  const kind = document.getElementById(`job-kind-${job.id}`);
  const msg = document.getElementById(`job-msg-${job.id}`);
  const out = document.getElementById(`job-result-${job.id}`);
  if (st) st.textContent = job.status;
  if (kind) kind.textContent = job.kind || 'routing';
  if (msg) msg.textContent = job.result_text || job.user_message || job.error || '';

  if (!out) return;
  if (job.status === 'done' || job.status === 'needs-review') {
    let html = '';
    if (job.image_b64) {
      html += `<img class="image" src="data:image/png;base64,${job.image_b64.replace(/^data:image\/\w+;base64,/, '')}" alt="Generated image">`;
      html += `<a class="artifact-link" href="/api/v1/manager/jobs/${job.id}/artifact" target="_blank">Open image artifact</a>`;
    } else if (job.artifact) {
      html += `<a class="artifact-link" href="/api/v1/manager/jobs/${job.id}/artifact" target="_blank">Download compressed artifact</a>`;
    }
    if (job.logs?.length) {
      html += `<pre>${escapeHtml(job.logs.slice(-10).join('\n'))}</pre>`;
    }
    out.innerHTML = html;
  }
  if (job.status === 'failed') {
    out.innerHTML = `<pre>${escapeHtml(job.error || 'failed')}</pre>`;
  }
}

async function refreshJobs() {
  try {
    const r = await fetch('/api/v1/manager/jobs', {cache:'no-store'});
    const j = await r.json();
    $('messages').innerHTML = '';
    for (const job of j.jobs || []) {
      addJobCard(job);
      updateJobCard(job);
      if (!['done','failed','needs-review'].includes(job.status)) pollJob(job.id);
    }
    if (!(j.jobs || []).length) add('system', 'No handoff jobs yet.');
  } catch(e) {
    add('system', e.message, 'error');
  }
}

async function ops(prompt) {
  const q = (prompt || '').toLowerCase();
  let url = '/api/v1/health';
  if (q.includes('vram')) url = '/api/v1/tools/vram';
  if (q.includes('cuda') || q.includes('toolchain') || q.includes('build info')) url = '/api/v1/tools/cuda';
  if (q.includes('model')) url = '/api/v1/tools/models';
  if (q.includes('catalog')) url = '/api/v1/catalog';
  if (q.includes('job')) url = '/api/v1/manager/jobs';
  try {
    const r = await fetch(url, {cache:'no-store'});
    add('assistant', JSON.stringify(await r.json(), null, 2));
  } catch(e) {
    add('assistant', e.message, 'error');
  }
}

function escapeHtml(text) {
  return String(text ?? '')
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#039;');
}

setTab('manager');
health();
setInterval(health, 6000);
