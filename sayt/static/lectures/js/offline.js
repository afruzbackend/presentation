/* Faqat oflayn (eksport qilingan) nusxa uchun: testni server o'rniga brauzer tekshiradi.
   Asosiy dasturda testlar Django'da tekshiriladi. */
(function () {
  const L = 'ABCD';
  // to'g'ri javob sahifada ochiq yozilmagan: har variant xeshlanib, savoldagi data-h bilan solishtiriladi
  function fnv1a(t) {
    let h = 0x811c9dc5;
    for (let i = 0; i < t.length; i++) { h ^= t.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
    return h.toString(16).padStart(8, '0');
  }
  function grade(p) { return p >= 86 ? 5 : p >= 71 ? 4 : p >= 56 ? 3 : 2; }
  const MSG = { 5: 'A’lo! Mavzuni to‘liq o‘zlashtirdingiz.', 4: 'Yaxshi natija! Biroz takrorlash kifoya.',
    3: 'Qoniqarli. Mavzuni yana bir bor ko‘rib chiqing.', 2: 'Mavzuni qayta o‘rganish tavsiya etiladi.' };

  document.querySelectorAll('form[data-offline]').forEach(form => {
    let blocks = Array.from(form.querySelectorAll('fieldset.qblock'));

    // Yakuniy test: savollar bazasidan tasodifiy N tasini qoldirish
    const pick = +form.dataset.pick;
    if (pick && blocks.length > pick) {
      const keep = new Set(blocks.slice().sort(() => Math.random() - .5).slice(0, pick));
      blocks.forEach(b => { if (!keep.has(b)) b.remove(); });
      blocks = blocks.filter(b => keep.has(b));
    }
    blocks.forEach((b, i) => { const n = b.querySelector('.qn'); if (n) n.textContent = i + 1; });

    form.addEventListener('submit', e => {
      e.preventDefault();
      let score = 0;
      const review = new Set();
      blocks.forEach(b => {
        const qid = b.querySelector('input').name.slice(1);
        const a = [0, 1, 2, 3].find(k => fnv1a(`${form.dataset.s}:${qid}:${k}`) === b.dataset.h);
        const chosen = b.querySelector('input:checked');
        const ok = chosen && +chosen.value === a;
        if (ok) score++; else review.add(b.dataset.topic);
        b.classList.add(ok ? 'is-ok' : 'is-bad');
        b.querySelectorAll('label.opt').forEach((lb, k) => {
          if (k === a) lb.classList.add('right'); else if (chosen && k === +chosen.value) lb.classList.add('wrong');
          lb.querySelector('input').disabled = true;
        });
      });
      const total = blocks.length, p = Math.round(score / total * 100), g = grade(p);
      const box = document.createElement('div');
      box.className = 'result-box';
      box.innerHTML = `<div class="ring-score" style="--p:${p}"><b>${p}%</b><small>${score} / ${total}</small></div>
        <h3>Baho: <span class="grade g${g}">${g}</span></h3><p>${MSG[g]}</p>
        <a class="btn primary" href="#" onclick="location.reload();return false;">Qayta topshirish</a>`;
      form.querySelector('.quiz-head').after(box);
      const foot = form.querySelector('.quiz-foot');
      if (foot) foot.remove();
      box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

  // index.html to'g'ridan-to'g'ri (file://) ochilsa YouTube pleyerni bloklaydi — qanday ochishni aytamiz
  if (location.protocol === 'file:') {
    document.querySelectorAll('.yt-player').forEach(p => {
      const n = document.createElement('div');
      n.className = 'yt-note';
      n.innerHTML = '<b>Videoni ko‘rish uchun</b> darslik papkasidagi <b>«Ochish.bat»</b> faylini ikki marta bosib oching.';
      p.appendChild(n);
    });
  }

  /* Server bajaradigan ishlar — statik nusxada brauzerda: tungi rejim, mavzu va atama qidiruvi */
  const params = new URLSearchParams(location.search);
  const low = s => (s || '').toLocaleLowerCase('uz');
  const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // tungi rejim: tanlov brauzerda eslab qolinadi
  document.querySelectorAll('[data-theme-btn]').forEach(btn => btn.addEventListener('click', e => {
    e.preventDefault();
    const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('theme', t); } catch (_) { /* xotira yopiq */ }
  }));

  // mundarija: ?f=Nazariy|Amaliy va ?q=... (Django'dagi bilan bir xil: nom, reja bandlari yoki raqam)
  const tf = document.querySelector('[data-topic-filter]');
  if (tf) {
    const kind = params.get('f') || 'all', q = (params.get('q') || '').trim();
    tf.querySelectorAll('button[name=f]').forEach(b => b.classList.toggle('on', b.value === kind));
    tf.querySelector('input[name=q]').value = q;
    let found = 0;
    document.querySelectorAll('.cgroup').forEach(g => {
      let shown = 0;
      g.querySelectorAll('.card').forEach(c => {
        const num = parseInt(c.querySelector('.card-num').textContent, 10);
        const text = low(c.querySelector('.card-title').textContent + ' ' + c.querySelector('.card-plan').textContent);
        const ok = (kind === 'all' || c.querySelector('.badge').textContent.trim() === kind)
          && (!q || text.includes(low(q)) || (/^\d+$/.test(q) && num === +q));
        c.hidden = !ok;
        if (ok) shown++;
      });
      g.hidden = !shown;
      g.querySelector('.cgroup-head small').textContent = shown + ' ta';
      found += shown;
    });
    const info = document.querySelector('.page-head p.muted');
    if (q && info) info.innerHTML = `«${esc(q)}» bo‘yicha ${found} ta mavzu topildi · <a class="link" href="mavzular.html">tozalash</a>`;
    if (!found) {
      const p = document.createElement('p');
      p.className = 'muted center';
      p.textContent = 'Hech narsa topilmadi.';
      document.querySelector('.cgroup')?.before(p);
    }
  }

  // glossariy: ?harf=K va ?q=... (atama yoki ta'rifida)
  const gf = document.querySelector('[data-gloss-filter]');
  if (gf) {
    const harf = params.get('harf') || '', q = low((params.get('q') || '').trim());
    gf.querySelector('input[name=q]').value = params.get('q') || '';
    document.querySelectorAll('.alpha a').forEach(a => a.classList.toggle('on', a.dataset.harf === harf));
    let letter = '', found = 0, total = 0, head = null, inHead = 0;
    const flush = () => { if (head) head.hidden = !inHead; };
    document.querySelectorAll('.gloss > *').forEach(el => {
      if (el.classList.contains('gloss-letter')) { flush(); head = el; inHead = 0; letter = el.textContent.trim(); return; }
      if (!el.classList.contains('gloss-item')) return;
      total++;
      const ok = (!harf || letter === harf) && (!q || low(el.textContent).includes(q));
      el.hidden = !ok;
      if (ok) { found++; inHead++; }
    });
    flush();
    const info = document.querySelector('.page-head p.muted');
    if ((harf || q) && info) info.innerHTML = `${total} ta atama · topildi: ${found} · <a class="link" href="glossariy.html">hammasi</a>`;
  }
})();
