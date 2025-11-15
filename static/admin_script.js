document.addEventListener('DOMContentLoaded', function(){
  const logsDiv = document.getElementById('logs');
  const fbDiv = document.getElementById('feedback');

  document.getElementById('loadLogs').addEventListener('click', async () => {
    logsDiv.innerHTML = 'Loading…';
    try {
      const res = await fetch('/admin/logs', { credentials: 'include' });
      if (res.status === 401) {
        logsDiv.innerHTML = '<em>Authentication required. Open <a href="/admin">/admin</a> in this browser and sign in, then try again.</em>';
        return;
      }
      const data = await res.json();
      if(!data || !data.length){ logsDiv.innerHTML = '<em>No logs found</em>'; return; }
      const html = data.map(item => {
        return `<div style="margin-bottom:12px">
                  <div><strong>${escapeHtml(item.timestamp || '')} — ${escapeHtml(item.model || '')}</strong></div>
                  <div class="small">input: ${escapeHtml((item.input_snippet||'').slice(0,200))}</div>
                  <pre>${escapeHtml(JSON.stringify(item.parsed || item.raw_response || {}, null, 2))}</pre>
                </div>`;
      }).join('');
      logsDiv.innerHTML = html;
    } catch(e){ logsDiv.innerHTML = `<em>Error: ${e.message}</em>`; }
  });

  document.getElementById('loadFeedback').addEventListener('click', async () => {
    fbDiv.innerHTML = 'Loading…';
    try {
      const res = await fetch('/admin/feedback', { credentials: 'include' });
      if (res.status === 401) {
        fbDiv.innerHTML = '<em>Authentication required. Open <a href="/admin">/admin</a> in this browser and sign in, then try again.</em>';
        return;
      }
      const data = await res.json();
      if(!data || !data.length){ fbDiv.innerHTML = '<em>No feedback rows</em>'; return; }
      let ths = Object.keys(data[0] || {}).map(h => `<th>${escapeHtml(h)}</th>`).join('');
      let trs = data.map(r => {
        let tds = Object.values(r).map(v => `<td>${escapeHtml(String(v||''))}</td>`).join('');
        return `<tr>${tds}</tr>`;
      }).join('');
      fbDiv.innerHTML = `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
    } catch(e){ fbDiv.innerHTML = `<em>Error: ${e.message}</em>`; }
  });

  document.getElementById('downloadLogs').addEventListener('click', () => {
    window.location = '/admin/download/llm_logs.jsonl';
  });
  document.getElementById('downloadFeedback').addEventListener('click', () => {
    window.location = '/admin/download/feedback.csv';
  });
  document.getElementById('downloadProcessed').addEventListener('click', () => {
    window.location = '/admin/download/processed_tickets.csv';
  });

  function escapeHtml(s){
    return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
  }
});