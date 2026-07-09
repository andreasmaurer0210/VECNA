// ── DICE ─────────────────────────────────────────────────────────────────

const diceHistory = [];

function quickRoll(expr) {
  document.getElementById('dice-input').value = expr;
  rollDice();
}

function rollDice() {
  const raw = document.getElementById('dice-input').value.trim();
  try {
    const result = evalDice(raw);
    document.getElementById('dice-result').textContent = result.total;
    addDiceHistory(raw, result);
  } catch(e) {
    document.getElementById('dice-result').textContent = '!';
    document.getElementById('dice-result').title = e.message;
  }
}

function evalDice(expr) {
  let e = expr.toLowerCase().replace(/\s+/g, '');
  let modifier = 0;

  const plusIdx = e.lastIndexOf('+');
  const minusIdx = e.lastIndexOf('-');
  const sepIdx = Math.max(plusIdx, minusIdx);

  if (sepIdx > 0 && e.indexOf('d') < sepIdx) {
    const sign = e[sepIdx] === '+' ? 1 : -1;
    modifier = sign * parseInt(e.slice(sepIdx + 1), 10);
    e = e.slice(0, sepIdx);
  }

  if (!e.includes('d')) throw new Error('Invalid dice expression');
  const [countStr, sidesStr] = e.split('d');
  const count = countStr ? parseInt(countStr, 10) : 1;
  const sides = parseInt(sidesStr, 10);

  if (isNaN(count) || isNaN(sides) || count < 1 || sides < 2 || count > 100)
    throw new Error('Invalid dice expression');

  const rolls = Array.from({length: count}, () => Math.floor(Math.random() * sides) + 1);
  const subtotal = rolls.reduce((a, b) => a + b, 0);
  return { rolls, modifier, subtotal, total: subtotal + modifier };
}

function addDiceHistory(expr, result) {
  diceHistory.unshift({ expr, result });
  if (diceHistory.length > 10) diceHistory.pop();
  const el = document.getElementById('dice-history-list');
  el.innerHTML = diceHistory.map(h => {
    const detail = h.result.rolls.join(' + ')
      + (h.result.modifier > 0 ? ` + ${h.result.modifier}` : h.result.modifier < 0 ? ` - ${Math.abs(h.result.modifier)}` : '');
    return `<div class="history-item">${h.expr} → [${detail}] = <span class="total">${h.result.total}</span></div>`;
  }).join('');
}

document.getElementById('dice-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') rollDice();
});
