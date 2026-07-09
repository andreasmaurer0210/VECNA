// ── Init ──────────────────────────────────────────────────────────────────

loadConfig().then(server => {
  SERVER = server;
  API = SERVER + '/api';
  return checkServer();
}).then(() => {
  loadMonsters();
  loadSpells();
  loadClasses();
});
