document.addEventListener('DOMContentLoaded', function(){
  const uploadForm = document.getElementById('uploadForm');
  const fileInput = document.getElementById('fileInput');
  const status = document.getElementById('status');
  const result = document.getElementById('result');
  const preview = document.getElementById('preview');
  const categoryEl = document.getElementById('category');
  const tagsEl = document.getElementById('tags');
  const priorityEl = document.getElementById('priority');
  const confidenceEl = document.getElementById('confidence');
  const solutionEl = document.getElementById('solution');
  const similarContainer = document.getElementById('similarContainer');
  const similarList = document.getElementById('similarList');

  const orig_text_input = document.getElementById('orig_text');
  const fbForm = document.getElementById('feedbackForm');
  const fbStatus = document.getElementById('fbStatus');

  if (uploadForm && fileInput) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      status.textContent = '';
      fbStatus.textContent = '';
      const file = fileInput.files[0];
      if(!file){ status.textContent = 'Choose a file first.'; return; }
      status.textContent = 'Uploading and analyzing…';

      const fd = new FormData();
      fd.append('file', file);

      try {
        const res = await fetch('/analyze', { method: 'POST', body: fd });
        const data = await res.json();
        if(res.status !== 200){ status.textContent = data.error || 'Analysis failed'; return; }

        status.textContent = 'Analysis complete';
        result.classList.remove('hidden');

        const uploaded = data.uploaded_ticket || data.llm_result?.text || '';
        preview.textContent = uploaded;

        categoryEl.textContent = data.category || data.llm_result?.category || '—';
        const tags = data.tags || data.llm_result?.tags || [];
        if(Array.isArray(tags) && tags.length){
          tagsEl.innerHTML = tags.map(t => `<span class="tags">${t}</span>`).join(' ');
        } else { tagsEl.textContent = '—'; }
        priorityEl.textContent = data.suggested_priority || data.llm_result?.suggested_priority || '—';
        confidenceEl.textContent = (data.confidence || data.llm_result?.confidence || '—');
        solutionEl.textContent = data.solution || data.llm_result?.solution || '—';

        if(data.similar_tickets && data.similar_tickets.length){
          similarContainer.style.display = 'block';
          similarList.innerHTML = data.similar_tickets.map(s=>{
            return `<div style="margin-bottom:8px">
                      <div class="small">score: ${s.similarity.toFixed(3)}</div>
                      <pre>${escapeHtml(s.snippet)}</pre>
                    </div>`;
          }).join('');
        } else {
          similarContainer.style.display = 'none';
          similarList.innerHTML = '';
        }
        // --- Recommended Articles UI ---
       const articleContainer = document.getElementById('articleContainer');
       const articleList = document.getElementById('articleList');
       articleList.innerHTML = ""; // clear previous

    if (data.recommended_articles && data.recommended_articles.length > 0) {
      articleContainer.style.display = 'block';

      data.recommended_articles.forEach(a => {
      const div = document.createElement('div');
      div.style.border = "1px solid #ccc";
      div.style.padding = "8px";
      div.style.margin = "6px 0";
      div.style.borderRadius = "6px";

      div.innerHTML = `
        <strong>${a.title}</strong> (${a.article_id})<br>
        <small>${a.summary}</small><br>
        <a href="${a.link}" target="_blank">View Full Article</a>`;

      articleList.appendChild(div);
     });

    } else {
       articleContainer.style.display = 'block';
       articleList.innerHTML = `<em>No matching knowledge base articles found.</em>`;
   }


        orig_text_input.value = uploaded;
      } catch(err){
        console.error(err);
        status.textContent = 'Error contacting server';
      }
    });
  }

  if (fbForm) {
    fbForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      fbStatus.textContent = '';
      const payload = {
        original_text: document.getElementById('orig_text').value,
        final_category: document.getElementById('final_category').value,
        final_tags: document.getElementById('final_tags').value.split(',').map(s=>s.trim()).filter(Boolean),
        final_priority: document.getElementById('final_priority').value,
        agent_note: document.getElementById('agent_note').value
      };
      try {
        const res = await fetch('/feedback', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(payload)
        });
        if(res.status === 200){ fbStatus.textContent = 'Feedback saved'; fbForm.reset(); }
        else { fbStatus.textContent = (await res.json()).error || 'Failed to save feedback'; }
      } catch(err){
        fbStatus.textContent = 'Network error';
      }
    });
  }

  function escapeHtml(s){
    return String(s || '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
  }
});