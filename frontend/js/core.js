let SERVER = '';
let API = '';

async function loadConfig() {
  const override = new URLSearchParams(location.search).get('server');
  if (override) return override.replace(/\/+$/, '');

  try {
    const response = await fetch('config.json', { cache: 'no-store' });
    if (response.ok) {
      const config = await response.json();
      if (config.server) return String(config.server).replace(/\/+$/, '');
    }
  } catch (e) {
    console.warn('VECNA config.json unavailable:', e);
  }

  return document.querySelector('meta[name="vecna-server"]').content.replace(/\/+$/, '');
}

// ── Server health check ───────────────────────────────────────────────────

async function checkServer() {
  const dot   = document.getElementById('status-dot');
  const label = document.getElementById('status-label');
  dot.className = 'status-dot checking';
  label.textContent = 'Connecting…';
  try {
    const r = await fetch(API + '/health', { signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    dot.className = 'status-dot ok';
    label.textContent = 'VECNA · online';
  } catch (e) {
    dot.className = 'status-dot error';
    label.textContent = 'VECNA · offline';
    console.error('VECNA server unreachable:', e);
  }
}

// ── Cache + fetch ─────────────────────────────────────────────────────────

const cache = {};

async function apiFetch(path) {
  if (cache[path]) return cache[path];
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`Server error ${r.status}`);
  const data = await r.json();
  cache[path] = data;
  return data;
}

// ── Tabs ──────────────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ── Search helper ─────────────────────────────────────────────────────────

function filterList(items, query) {
  const q = query.toLowerCase();
  return items.filter(i => i.name.toLowerCase().includes(q) || i.index.includes(q));
}

// ── Stat modifier helper ──────────────────────────────────────────────────

function mod(score) {
  const m = Math.floor((score - 10) / 2);
  return m >= 0 ? `+${m}` : `${m}`;
}
