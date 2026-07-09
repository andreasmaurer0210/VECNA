// ── MONSTERS ─────────────────────────────────────────────────────────────

let allMonsters = [];

async function loadMonsters() {
  const data = await apiFetch('/monsters');
  allMonsters = data.results;
  renderMonsterList(allMonsters);
}

function renderMonsterList(items) {
  const el = document.getElementById('monster-list');
  if (!items.length) { el.innerHTML = '<div class="empty-msg">No results</div>'; return; }
  el.innerHTML = items.map(m =>
    `<div class="list-item" data-index="${m.index}" onclick="loadMonster('${m.index}', this)">
      <span class="name">${m.name}</span>
     </div>`
  ).join('');
}

async function loadMonster(index, el) {
  document.querySelectorAll('#monster-list .list-item').forEach(i => i.classList.remove('selected'));
  if (el) el.classList.add('selected');
  const detail = document.getElementById('monster-detail');
  detail.innerHTML = '<div class="loading-msg">Loading…</div>';
  try {
    const d = await apiFetch(`/monsters/${index}`);
    renderMonster(d, detail);
  } catch(e) {
    detail.innerHTML = `<div class="empty-msg">Error: ${e.message}</div>`;
  }
}

function renderMonster(d, el) {
  const ac = Array.isArray(d.armor_class)
    ? d.armor_class.map(a => `${a.value} (${a.type})`).join(', ')
    : d.armor_class ?? '?';
  const speed = Object.entries(d.speed || {}).map(([k,v]) => `${k} ${v}`).join(', ');

  const diIcons = d.damage_immunities?.length
    ? `<div class="info-item"><div class="lbl">Damage Immunities</div><div class="val">${d.damage_immunities.join(', ')}</div></div>` : '';
  const drIcons = d.damage_resistances?.length
    ? `<div class="info-item"><div class="lbl">Damage Resistances</div><div class="val">${d.damage_resistances.join(', ')}</div></div>` : '';

  const senses = Object.entries(d.senses || {}).map(([k,v]) => `${k}: ${v}`).join(' · ');

  const specialAbilities = (d.special_abilities || []).map(a =>
    `<div class="ability-entry"><div class="aname">${a.name}</div><div class="adesc">${a.desc || ''}</div></div>`
  ).join('');

  const actions = (d.actions || []).map(a =>
    `<div class="ability-entry"><div class="aname">${a.name}</div><div class="adesc">${a.desc || ''}</div></div>`
  ).join('');

  el.innerHTML = `
    <div class="card">
      <div class="card-title">${d.name}</div>
      <div class="card-subtitle">${d.size ?? ''} ${d.type ?? ''} · ${d.alignment ?? ''}</div>
      <div class="info-row">
        <div class="info-item"><div class="lbl">Armor Class</div><div class="val">${ac}</div></div>
        <div class="info-item"><div class="lbl">Hit Points</div><div class="val">${d.hit_points} (${d.hit_dice})</div></div>
        <div class="info-item"><div class="lbl">Speed</div><div class="val">${speed}</div></div>
        <div class="info-item"><div class="lbl">Challenge Rating</div><div class="val"><span class="tag red">CR ${d.challenge_rating}</span></div></div>
        <div class="info-item"><div class="lbl">XP</div><div class="val">${d.xp}</div></div>
        <div class="info-item"><div class="lbl">Proficiency Bonus</div><div class="val">+${d.proficiency_bonus}</div></div>
      </div>

      <div class="section-header">Ability Scores</div>
      <div class="stat-grid">
        ${['strength','dexterity','constitution','intelligence','wisdom','charisma'].map(s => `
          <div class="stat-box">
            <div class="label">${s.slice(0,3).toUpperCase()}</div>
            <div class="value">${d[s]}</div>
            <div class="mod">${mod(d[s])}</div>
          </div>`).join('')}
      </div>

      ${senses ? `<div class="info-row" style="margin-top:10px">
        <div class="info-item"><div class="lbl">Senses</div><div class="val">${senses}</div></div>
      </div>` : ''}
      ${d.languages ? `<div class="info-row">
        <div class="info-item"><div class="lbl">Languages</div><div class="val">${d.languages}</div></div>
      </div>` : ''}
      ${diIcons || drIcons ? `<div class="info-row">${diIcons}${drIcons}</div>` : ''}
    </div>

    ${specialAbilities ? `<div class="card">
      <div class="section-header">Special Abilities</div>
      <div class="ability-list">${specialAbilities}</div>
    </div>` : ''}

    ${actions ? `<div class="card">
      <div class="section-header">Actions</div>
      <div class="ability-list">${actions}</div>
    </div>` : ''}
  `;
}

document.getElementById('monster-search').addEventListener('input', e => {
  renderMonsterList(filterList(allMonsters, e.target.value));
});
