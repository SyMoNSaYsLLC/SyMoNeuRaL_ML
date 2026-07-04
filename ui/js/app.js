const $ = (sel) => document.querySelector(sel);
const messages = $('#messages');
const welcome = $('#welcome');
const form = $('#chatForm');
const promptEl = $('#prompt');
const sendBtn = $('#sendBtn');
const fileInput = $('#fileInput');
const attachmentTray = $('#attachmentTray');
const modelSelect = $('#modelSelect');
const chatList = $('#chatList');
const chatSearch = $('#chatSearch');
const mcpList = $('#mcpList');
const drawer = $('#drawer');
const drawerTitle = $('#drawerTitle');
const drawerEyebrow = $('#drawerEyebrow');
const drawerBody = $('#drawerBody');

const state = {
  chats: JSON.parse(localStorage.getItem('symon.chats') || '[]'),
  activeChatId: null,
  reasoning: localStorage.getItem('symon.reasoning') || 'auto',
  files: [],
  enabledTools: new Set(JSON.parse(localStorage.getItem('symon.tools') || '["manager","artifacts"]')),
  enabledMcp: new Set(JSON.parse(localStorage.getItem('symon.mcp') || '["matlab-mcp","prompt-library"]')),
  settings: JSON.parse(localStorage.getItem('symon.settings') || '{"api":"/api/v1/manager/submit","pollMs":1400,"timeoutMs":720000}')
};

const mcpServers = [
  { id: 'matlab-mcp', name: 'MATLAB MCP Server', desc: 'MATLAB research/tool bridge', status: 'available' },
  { id: 'prompt-library', name: 'AI Coding Prompts', desc: 'Local prompt library', status: 'available' },
  { id: 'iptv', name: 'IPTV Library', desc: 'Playlist/index search bridge', status: 'available' },
  { id: 'filesystem', name: 'Local Files', desc: 'File-aware project work', status: 'planned' },
  { id: 'git', name: 'Git/Repo Tools', desc: 'Commit, diff, migration workflows', status: 'planned' }
];

const tools = [
  { id: 'manager', name: 'SyMoNeuRaL Manager', desc: 'Routes chat/code/image/helper requests.' },
  { id: 'artifacts', name: 'Artifacts', desc: 'Allows generated files/images to show as links.' },
  { id: 'iptv-search', name: 'IPTV Search', desc: 'Searches local IPTV index when requested.' },
  { id: 'matlab', name: 'MATLAB Tools', desc: 'Uses MATLAB research wrappers when available.' },
  { id: 'web-ui', name: 'UI Builder', desc: 'Frontend/code update workflows.' }
];

const prompts = [
  'Review the repo status and tell me the next safest build step.',
  'Create a migration plan and list overlaps before code changes.',
  'Search my IPTV index for this topic and summarize the matches.',
  'Design this as a Rust runtime module but keep Python orchestration for now.',
  'Explain what will break before suggesting a patch.',
  'Generate exact commands only and use sudo rm -rf for destructive removals.'
];

function persist() {
  localStorage.setItem('symon.chats', JSON.stringify(state.chats.slice(0, 80)));
  localStorage.setItem('symon.reasoning', state.reasoning);
  localStorage.setItem('symon.tools', JSON.stringify([...state.enabledTools]));
  localStorage.setItem('symon.mcp', JSON.stringify([...state.enabledMcp]));
  localStorage.setItem('symon.settings', JSON.stringify(state.settings));
}
function escapeText(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function nowLabel() { return new Date().toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }); }
function currentChat() { return state.chats.find(c => c.id === state.activeChatId); }
function ensureChat(title='New chat') {
  if (state.activeChatId && currentChat()) return currentChat();
  const chat = { id: crypto.randomUUID(), title, created: Date.now(), updated: Date.now(), messages: [] };
  state.chats.unshift(chat); state.activeChatId = chat.id; persist(); renderChatList(); return chat;
}
function saveMessage(role, text, meta={}) {
  const chat = ensureChat(text.slice(0, 40) || 'New chat');
  if (chat.title === 'New chat' && role === 'user') chat.title = text.slice(0, 54) || 'New chat';
  chat.messages.push({ role, text, meta, at: Date.now() }); chat.updated = Date.now();
  state.chats = [chat, ...state.chats.filter(c => c.id !== chat.id)]; state.activeChatId = chat.id; persist(); renderChatList();
}
function hideWelcome(){ welcome?.classList.add('hidden'); }
function scrollDown(){ messages.scrollTop = messages.scrollHeight; }
function addMessage(role, text, opts={}) {
  hideWelcome();
  const row = document.createElement('div'); row.className = `message ${role}`;
  const b = document.createElement('div'); b.className = 'bubble';
  if (opts.html) b.innerHTML = text; else b.textContent = text || '';
  if (opts.artifactUrl) { const a = document.createElement('a'); a.className = 'artifact'; a.href = opts.artifactUrl; a.target = '_blank'; a.rel = 'noreferrer'; a.textContent = opts.artifactLabel || 'Open artifact'; b.appendChild(a); }
  if (opts.imageUrl) { const img = document.createElement('img'); img.className = 'image'; img.src = opts.imageUrl; img.alt = 'Generated image'; b.appendChild(img); }
  row.appendChild(b); messages.appendChild(row); scrollDown(); return row;
}
function thinking(){ return addMessage('assistant', '<span class="thinking"><i></i><i></i><i></i></span>', {html:true}); }
function replace(row, text, opts={}) { const b=row.querySelector('.bubble'); b.innerHTML=''; b.textContent=text||''; if(opts.artifactUrl){ const a=document.createElement('a'); a.className='artifact'; a.href=opts.artifactUrl; a.target='_blank'; a.rel='noreferrer'; a.textContent=opts.artifactLabel||'Open artifact'; b.appendChild(a);} if(opts.imageUrl){const img=document.createElement('img'); img.className='image'; img.src=opts.imageUrl; img.alt='Generated image'; b.appendChild(img);} scrollDown(); }
function autosize(){ promptEl.style.height='auto'; promptEl.style.height=Math.min(promptEl.scrollHeight,220)+'px'; }
async function json(url, options={}) { const r=await fetch(url,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options}); const t=await r.text(); let d={}; if(t){ try{d=JSON.parse(t)}catch{d={raw:t}} } if(!r.ok) throw new Error(d.detail||d.error||d.raw||`${r.status} ${r.statusText}`); return d; }
async function waitJob(id,row){ const start=Date.now(); while(Date.now()-start < Number(state.settings.timeoutMs||720000)){ const job=await json(`/api/v1/manager/jobs/${encodeURIComponent(id)}?include_image=false`); if(job.status==='done'){ const url=(job.artifact||job.image_path)?`/api/v1/manager/jobs/${encodeURIComponent(job.id)}/artifact`:null; const text=job.result_text||job.user_message||'Done.'; replace(row,text,{artifactUrl:url,artifactLabel:job.image_path?'Open image':url?'Open artifact':null,imageUrl:job.image_path?url:null}); saveMessage('assistant', text, {artifactUrl:url}); return; } if(job.status==='failed'){ const text=job.error||'The request failed.'; replace(row,text); saveMessage('assistant', text); return; } await new Promise(r=>setTimeout(r, Number(state.settings.pollMs||1400))); } throw new Error('Timed out waiting for the backend'); }
function buildPrompt(text){
  const fileNote = state.files.length ? '\n\nAttached file names for this request:\n' + state.files.map(f => `- ${f.name} (${f.size} bytes)`).join('\n') : '';
  return text + fileNote;
}
async function submitPrompt(text){
  addMessage('user', text); saveMessage('user', text, { model:modelSelect.value, reasoning: state.reasoning, files: state.files.map(f=>f.name) });
  const row=thinking(); sendBtn.disabled=true; promptEl.disabled=true;
  try{
    const payload = {
      prompt: buildPrompt(text),
      model: modelSelect.value,
      reasoning_level: state.reasoning,
      tools: [...state.enabledTools],
      mcp_servers: [...state.enabledMcp],
      attachments: state.files.map(f => ({ name:f.name, size:f.size, type:f.type || 'application/octet-stream' }))
    };
    const submitted=await json(state.settings.api || '/api/v1/manager/submit',{method:'POST',body:JSON.stringify(payload)});
    const id=submitted.id||submitted.job_id;
    if(!id){ const answer=submitted.result_text||submitted.message||'Submitted.'; replace(row,answer); saveMessage('assistant', answer); return; }
    await waitJob(id,row);
  } catch(err){ const text=`Error: ${err.message||err}`; replace(row,text); saveMessage('assistant', text); }
  finally{ sendBtn.disabled=false; promptEl.disabled=false; state.files=[]; renderFiles(); promptEl.focus(); }
}
function renderChatList(){
  const q=(chatSearch.value||'').toLowerCase(); chatList.innerHTML='';
  state.chats.filter(c => !q || c.title.toLowerCase().includes(q) || c.messages.some(m => String(m.text).toLowerCase().includes(q))).slice(0,60).forEach(c=>{
    const btn=document.createElement('button'); btn.className='chatItem'+(c.id===state.activeChatId?' active':''); btn.innerHTML=`<b>${escapeText(c.title||'New chat')}</b><span>${nowLabel(c.updated||c.created)} • ${c.messages.length} messages</span>`;
    btn.onclick=()=>loadChat(c.id); chatList.appendChild(btn);
  });
  if(!chatList.children.length){ const div=document.createElement('div'); div.className='chatItem'; div.innerHTML='<b>No chats yet</b><span>Start a new chat</span>'; chatList.appendChild(div); }
}
function loadChat(id){ state.activeChatId=id; messages.innerHTML=''; const chat=currentChat(); if(!chat || !chat.messages.length){ messages.appendChild(welcome); welcome.classList.remove('hidden'); return; } chat.messages.forEach(m=>addMessage(m.role,m.text)); renderChatList(); }
function newChat(){ state.activeChatId=null; messages.innerHTML=''; messages.appendChild(welcome); welcome.classList.remove('hidden'); promptEl.value=''; autosize(); renderChatList(); promptEl.focus(); }
function renderMcpList(){
  const q=(chatSearch.value||'').toLowerCase(); mcpList.innerHTML='';
  mcpServers.filter(s => !q || s.name.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q)).forEach(s=>{
    const active=state.enabledMcp.has(s.id); const btn=document.createElement('button'); btn.className='mcpItem'+(active?' active':'');
    btn.innerHTML=`<b>${escapeText(s.name)}</b><span>${escapeText(s.desc)} • ${s.status}${active?' • enabled':''}</span>`;
    btn.onclick=()=>{ active?state.enabledMcp.delete(s.id):state.enabledMcp.add(s.id); persist(); renderMcpList(); };
    mcpList.appendChild(btn);
  });
}
function renderFiles(){ attachmentTray.innerHTML=''; state.files.forEach((f,i)=>{ const chip=document.createElement('button'); chip.type='button'; chip.className='fileChip'; chip.textContent=`${f.name} ×`; chip.onclick=()=>{state.files.splice(i,1); renderFiles();}; attachmentTray.appendChild(chip); }); }
function openDrawer(kind){ drawer.classList.add('open'); drawer.setAttribute('aria-hidden','false'); drawerBody.innerHTML='';
  if(kind==='settings') renderSettings(); if(kind==='prompts') renderPrompts(); if(kind==='tools') renderTools(); if(kind==='mcp') renderMcpPanel(); }
function closeDrawer(){ drawer.classList.remove('open'); drawer.setAttribute('aria-hidden','true'); }
function renderSettings(){ drawerEyebrow.textContent='Local UI'; drawerTitle.textContent='Settings'; drawerBody.innerHTML=`
  <div class="panelCard"><h3>One server UI</h3><p>This end-user console is served on <code>127.0.0.1:8000</code>. Port 8080 can stay as the engine test endpoint.</p></div>
  <div class="field"><label>Manager submit endpoint</label><input id="apiField" value="${escapeText(state.settings.api)}"></div>
  <div class="field"><label>Polling milliseconds</label><input id="pollField" type="number" value="${escapeText(state.settings.pollMs)}"></div>
  <div class="field"><label>Timeout milliseconds</label><input id="timeoutField" type="number" value="${escapeText(state.settings.timeoutMs)}"></div>
  <button class="newChat" id="saveSettings">Save settings</button>`;
  $('#saveSettings').onclick=()=>{ state.settings.api=$('#apiField').value.trim()||'/api/v1/manager/submit'; state.settings.pollMs=Number($('#pollField').value||1400); state.settings.timeoutMs=Number($('#timeoutField').value||720000); persist(); closeDrawer(); };
}
function renderPrompts(){ drawerEyebrow.textContent='Prompt library'; drawerTitle.textContent='Prompts'; prompts.forEach(p=>{ const card=document.createElement('button'); card.className='panelCard'; card.style.textAlign='left'; card.innerHTML=`<h3>${escapeText(p.slice(0,42))}</h3><p>${escapeText(p)}</p>`; card.onclick=()=>{ promptEl.value = promptEl.value ? promptEl.value + '\n\n' + p : p; autosize(); closeDrawer(); promptEl.focus(); }; drawerBody.appendChild(card); }); }
function renderTools(){ drawerEyebrow.textContent='Tool routing'; drawerTitle.textContent='Tools'; tools.forEach(t=>{ const active=state.enabledTools.has(t.id); const card=document.createElement('button'); card.className='panelCard'; card.style.textAlign='left'; card.innerHTML=`<h3>${active?'✓ ':'＋ '}${escapeText(t.name)}</h3><p>${escapeText(t.desc)}</p>`; card.onclick=()=>{ active?state.enabledTools.delete(t.id):state.enabledTools.add(t.id); persist(); renderTools(); }; drawerBody.appendChild(card); }); }
function renderMcpPanel(){ drawerEyebrow.textContent='MCP'; drawerTitle.textContent='MCP servers'; mcpServers.forEach(s=>{ const active=state.enabledMcp.has(s.id); const card=document.createElement('button'); card.className='panelCard'; card.style.textAlign='left'; card.innerHTML=`<h3>${active?'✓ ':'＋ '}${escapeText(s.name)}</h3><p>${escapeText(s.desc)}<br>Status: ${escapeText(s.status)}</p>`; card.onclick=()=>{ active?state.enabledMcp.delete(s.id):state.enabledMcp.add(s.id); persist(); renderMcpPanel(); renderMcpList(); }; drawerBody.appendChild(card); }); }

form.addEventListener('submit', e=>{ e.preventDefault(); const text=promptEl.value.trim(); if(!text)return; promptEl.value=''; autosize(); submitPrompt(text); });
promptEl.addEventListener('input', autosize);
promptEl.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); form.requestSubmit(); }});
fileInput.addEventListener('change', e=>{ state.files.push(...Array.from(e.target.files||[])); fileInput.value=''; renderFiles(); });
$('#attachBtn').onclick=()=>fileInput.click();
$('#newChatBtn').onclick=newChat; $('#clearChatsBtn').onclick=()=>{ if(confirm('Clear local chat history in this browser?')){ state.chats=[]; state.activeChatId=null; persist(); newChat(); }};
chatSearch.addEventListener('input', ()=>{ renderChatList(); renderMcpList(); });
$('#settingsBtn').onclick=()=>openDrawer('settings'); $('#promptsBtn').onclick=()=>openDrawer('prompts'); $('#toolsBtn').onclick=()=>openDrawer('tools'); $('#mcpBtn').onclick=()=>openDrawer('mcp');
$('#addPromptBtn').onclick=()=>openDrawer('prompts'); $('#addToolBtn').onclick=()=>openDrawer('tools'); $('#addMcpBtn').onclick=()=>openDrawer('mcp');
$('#closeDrawer').onclick=closeDrawer; drawer.addEventListener('click', e=>{ if(e.target===drawer) closeDrawer(); });
$('#collapseSidebar').onclick=()=>document.querySelector('.app').dataset.sidebar = document.querySelector('.app').dataset.sidebar === 'open' ? 'closed' : 'open';
$('#mobileSidebarBtn').onclick=()=>document.querySelector('.app').dataset.sidebar='open';
document.querySelectorAll('[data-reasoning]').forEach(btn=>{ if(btn.dataset.reasoning===state.reasoning) btn.classList.add('active'); else btn.classList.remove('active'); btn.onclick=()=>{ state.reasoning=btn.dataset.reasoning; document.querySelectorAll('[data-reasoning]').forEach(b=>b.classList.toggle('active', b===btn)); persist(); }; });
document.querySelectorAll('.quickPrompt').forEach(btn=>{ btn.onclick=()=>{ promptEl.value=btn.textContent.trim(); autosize(); promptEl.focus(); }; });
modelSelect.value = localStorage.getItem('symon.model') || 'auto'; modelSelect.onchange=()=>localStorage.setItem('symon.model', modelSelect.value);
renderChatList(); renderMcpList(); renderFiles(); autosize(); promptEl.focus();
