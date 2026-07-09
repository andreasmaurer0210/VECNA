// ── CLASSES ───────────────────────────────────────────────────────────────

let allClasses = [];

async function loadClasses() {
  const data = await apiFetch('/classes');
  allClasses = data.results;
  renderClassList(allClasses);
}

function renderClassList(items) {
  const el = document.getElementById('class-list');
  if (!items.length) { el.innerHTML = '<div class="empty-msg">No results</div>'; return; }
  el.innerHTML = items.map(c =>
    `<div class="list-item" data-index="${c.index}" onclick="loadClass('${c.index}', this)">
      <span class="name">${c.name}</span>
    </div>`
  ).join('');
}

async function loadClass(index, el) {
  document.querySelectorAll('#class-list .list-item').forEach(i => i.classList.remove('selected'));
  if (el) el.classList.add('selected');
  const detail = document.getElementById('class-detail');
  detail.innerHTML = '<div class="loading-msg">Loading…</div>';
  try {
    const d = await apiFetch(`/classes/${index}`);
    renderClass(d, detail);
  } catch(e) {
    detail.innerHTML = `<div class="empty-msg">Error: ${e.message}</div>`;
  }
}

function renderClass(d, el) {
  const saves = (d.saving_throws || []).map(s => `<span class="tag gold">${s.name}</span>`).join('');
  const subclasses = (d.subclasses || []).map(s => `<span class="tag">${s.name}</span>`).join('');
  const profs = (d.proficiencies || []).map(p => `<span class="tag">${p.name}</span>`).join('');

  let profChoices = '';
  if (d.proficiency_choices?.length) {
    profChoices = d.proficiency_choices.map(pc => {
      const opts = (pc.from?.options || []).map(o => o.item?.name ?? o.choice?.desc ?? '?').join(', ');
      return `<div class="info-item" style="flex-basis:100%"><div class="lbl">Choose ${pc.choose}</div><div class="val" style="font-size:0.85rem;color:var(--muted)">${opts}</div></div>`;
    }).join('');
  }

  let startEq = '';
  if (d.starting_equipment?.length) {
    startEq = d.starting_equipment.map(e =>
      `<span class="tag">${e.equipment?.name ?? '?'} ×${e.quantity}</span>`
    ).join('');
  }

  el.innerHTML = `
    <div class="card">
      <div class="card-title">${d.name}</div>
      <div class="card-subtitle">Base Class</div>
      <div class="info-row">
        <div class="info-item"><div class="lbl">Hit Die</div><div class="val"><span class="tag red">d${d.hit_die}</span></div></div>
        <div class="info-item"><div class="lbl">Saving Throws</div><div class="val">${saves}</div></div>
        <div class="info-item"><div class="lbl">Subclasses</div><div class="val">${subclasses}</div></div>
      </div>

      <div class="section-header">Proficiencies</div>
      <div>${profs || '<span style="color:var(--muted)">—</span>'}</div>

      ${profChoices ? `<div class="section-header">Proficiency Choices</div><div class="info-row" style="flex-direction:column;gap:8px">${profChoices}</div>` : ''}

      ${startEq ? `<div class="section-header">Starting Equipment</div><div>${startEq}</div>` : ''}
    </div>
  `;
}

document.getElementById('class-search').addEventListener('input', e => {
  renderClassList(filterList(allClasses, e.target.value));
});
