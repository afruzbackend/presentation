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
})();
