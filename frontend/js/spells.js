// ── SPELLS ───────────────────────────────────────────────────────────────

let allSpells = [];

async function loadSpells() {
  const data = await apiFetch('/spells');
  allSpells = data.results;
  renderSpellList(allSpells);
}

function renderSpellList(items) {
  const el = document.getElementById('spell-list');
  if (!items.length) { el.innerHTML = '<div class="empty-msg">No results</div>'; return; }
  el.innerHTML = items.map(s => {
    const lvl = s.level === 0 ? 'Cantrip' : `Lvl ${s.level}`;
    return `<div class="list-item" data-index="${s.index}" onclick="loadSpell('${s.index}', this)">
      <span class="name">${s.name}</span>
      <span class="badge badge-level">${lvl}</span>
    </div>`;
  }).join('');
}

async function loadSpell(index, el) {
  document.querySelectorAll('#spell-list .list-item').forEach(i => i.classList.remove('selected'));
  if (el) el.classList.add('selected');
  const detail = document.getElementById('spell-detail');
  detail.innerHTML = '<div class="loading-msg">Loading…</div>';
  try {
    const d = await apiFetch(`/spells/${index}`);
    renderSpell(d, detail);
  } catch(e) {
    detail.innerHTML = `<div class="empty-msg">Error: ${e.message}</div>`;
  }
}

function renderSpell(d, el) {
  const school = d.school?.name ?? '?';
  const level = d.level === 0 ? 'Cantrip' : `Level ${d.level}`;
  const classes = (d.classes || []).map(c => `<span class="tag">${c.name}</span>`).join('');
  const components = (d.components || []).join(', ') + (d.material ? ` (${d.material})` : '');
  const desc = (d.desc || []).join('<br/><br/>');
  const higher = (d.higher_level || []).join(' ');

  let dmgHtml = '';
  if (d.damage?.damage_at_slot_level) {
    const rows = Object.entries(d.damage.damage_at_slot_level)
      .map(([slot, dmg]) => `<span class="tag gold">Slot ${slot}: ${dmg}</span>`).join('');
    dmgHtml = `<div class="section-header">Damage by Slot Level</div><div>${rows}</div>`;
  }

  let aoeHtml = '';
  if (d.area_of_effect) {
    aoeHtml = `<div class="info-item"><div class="lbl">Area of Effect</div><div class="val">${d.area_of_effect.size} ft ${d.area_of_effect.type}</div></div>`;
  }

  el.innerHTML = `
    <div class="card">
      <div class="card-title">${d.name}</div>
      <div class="card-subtitle">${level} · ${school}</div>
      <div class="info-row">
        <div class="info-item"><div class="lbl">Casting Time</div><div class="val">${d.casting_time}</div></div>
        <div class="info-item"><div class="lbl">Range</div><div class="val">${d.range}</div></div>
        <div class="info-item"><div class="lbl">Components</div><div class="val">${components}</div></div>
        <div class="info-item"><div class="lbl">Duration</div><div class="val">${d.duration}</div></div>
        ${d.concentration ? `<div class="info-item"><div class="lbl">Concentration</div><div class="val"><span class="tag gold">Yes</span></div></div>` : ''}
        ${d.ritual ? `<div class="info-item"><div class="lbl">Ritual</div><div class="val"><span class="tag">Ritual</span></div></div>` : ''}
        ${aoeHtml}
      </div>
      <div class="info-row"><div class="info-item"><div class="lbl">Classes</div><div class="val">${classes}</div></div></div>

      <div class="section-header">Description</div>
      <div class="desc-text">${desc}</div>

      ${higher ? `<div class="section-header">At Higher Levels</div><div class="desc-text">${higher}</div>` : ''}
      ${dmgHtml}
    </div>
  `;
}

document.getElementById('spell-search').addEventListener('input', e => {
  renderSpellList(filterList(allSpells, e.target.value));
});
