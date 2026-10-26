/* Ixtiyoriy qulayliklar: ← → slaydlar, Backspace — orqaga, Esc oynani yopish, sichqoncha bilan 3D egilish.
   Butun mantiq Django'da — bu fayl o'chirilsa ham sayt ishlayveradi. */
(function () {
  const b = document.body;
  addEventListener('keydown', e => {
    if (e.target.closest('input, textarea') || e.ctrlKey || e.altKey || e.metaKey) return;
    const open = location.hash && location.hash !== '#yopish';
    if (e.key === 'Escape' && open) { location.hash = 'yopish'; return; }
    if (open) return;
    if ((e.key === 'ArrowRight' || e.key === 'PageDown') && b.dataset.next) location.href = b.dataset.next;
    if ((e.key === 'ArrowLeft' || e.key === 'PageUp') && b.dataset.prev) location.href = b.dataset.prev;
    if (e.key === '/') { e.preventDefault(); location.hash = 'jumper'; }
    const back = document.querySelector('[data-back]');
    if (e.key === 'Backspace' && back) { e.preventDefault(); location.href = back.href; }
  });

  let raf = 0;
  addEventListener('pointermove', e => {
    const x = e.clientX / innerWidth - .5, y = e.clientY / innerHeight - .5;
    const card = e.target.closest && e.target.closest('[data-tilt]');
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      document.querySelectorAll('.s-tilt').forEach(t => { t.style.transform = `rotateX(${-y * 16}deg) rotateY(${x * 22}deg)`; });
      document.querySelectorAll('[data-follow]').forEach(t => { t.style.transform = `rotateX(${-y * 14}deg) rotateY(${x * 18}deg)`; });
      document.querySelectorAll('[data-tilt].tilting').forEach(c => { if (c !== card) { c.classList.remove('tilting'); c.style.removeProperty('--rx'); c.style.removeProperty('--ry'); } });
      if (!card) return;
      const r = card.getBoundingClientRect();
      card.classList.add('tilting');
      card.style.setProperty('--rx', ((.5 - (e.clientY - r.top) / r.height) * 10).toFixed(2) + 'deg');
      card.style.setProperty('--ry', (((e.clientX - r.left) / r.width - .5) * 12).toFixed(2) + 'deg');
    });
  });

  /* Bir vaqtda faqat bitta video: biri boshlansa, sahifadagi qolganlari to'xtaydi.
     YouTube — pleyer buyrug'i (postMessage), MP4 — oddiy <video>. */
  const ytFrames = () => Array.from(document.querySelectorAll('.yt-player iframe'));
  const ytSend = (f, msg) => { try { f.contentWindow.postMessage(JSON.stringify(msg), '*'); } catch (_) { /* yopilgan */ } };

  function pauseOthers(current) {
    document.querySelectorAll('video').forEach(v => { if (v !== current && !v.paused) v.pause(); });
    ytFrames().forEach(f => {
      if (f !== current && f.dataset.live) ytSend(f, { event: 'command', func: 'pauseVideo', args: [] });
    });
  }

  // MP4: «play» hodisasi
  document.addEventListener('play', e => { if (e.target.tagName === 'VIDEO') pauseOthers(e.target); }, true);

  // YouTube: muqova bosilganda u sahifaga {ytStart: 1} xabarini yuboradi (muqova bizniki — youtube.py),
  // keyin iframe YouTube pleyeriga o'tadi.
  function ytStarted(f) {
    f.dataset.live = '1';
    pauseOthers(f);
    // pleyer holatini (ijro / pauza) bizga yuborib tursin
    [800, 2000, 4000].forEach(ms => setTimeout(() => ytSend(f, { event: 'listening', id: 1, channel: 'widget' }), ms));
  }

  // YouTube pleyeri «ijro etilmoqda» desa (masalan, pauzadan qayta boshlansa) — qolganlarini to'xtatish
  addEventListener('message', e => {
    if (e.data && e.data.ytStart) {
      const f = ytFrames().find(x => x.contentWindow === e.source);
      if (f) ytStarted(f);
      return;
    }
    if (!/(^|\.)youtube(-nocookie)?\.com$/.test((e.origin || '').replace(/^https?:\/\//, ''))) return;
    let d;
    try { d = typeof e.data === 'string' ? JSON.parse(e.data) : e.data; } catch (_) { return; }
    const state = d && d.info && d.info.playerState;
    if (d && d.event === 'infoDelivery' && state === 1) {
      const f = ytFrames().find(x => x.contentWindow === e.source);
      if (f) pauseOthers(f);
    }
  });
})();
