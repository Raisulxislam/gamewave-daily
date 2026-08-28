(function () {
  var hero = document.getElementById('hero');
  if (!hero) return;

  var slides = hero.querySelectorAll('.hero-slide');
  var dotsWrap = hero.querySelector('.hero-dots');
  var prev = hero.querySelector('.hero-prev');
  var next = hero.querySelector('.hero-next');
  var current = 0;
  var timer = null;

  if (!slides.length) return;

  slides.forEach(function (_, i) {
    var d = document.createElement('button');
    d.className = 'hero-dot' + (i === 0 ? ' active' : '');
    d.setAttribute('aria-label', 'Slide ' + (i + 1));
    d.addEventListener('click', function () { goto(i); restart(); });
    dotsWrap.appendChild(d);
  });

  var dots = dotsWrap.children;

  function goto(i) {
    slides[current].classList.remove('active');
    dots[current].classList.remove('active');
    current = (i + slides.length) % slides.length;
    slides[current].classList.add('active');
    dots[current].classList.add('active');
  }

  function restart() {
    clearInterval(timer);
    timer = setInterval(function () { goto(current + 1); }, 6000);
  }

  prev.addEventListener('click', function () { goto(current - 1); restart(); });
  next.addEventListener('click', function () { goto(current + 1); restart(); });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') { goto(current - 1); restart(); }
    if (e.key === 'ArrowRight') { goto(current + 1); restart(); }
  });

  restart();
})();

(function () {
  var btnWrap = document.querySelector('.x-lang');
  if (!btnWrap) return;

  var btns = btnWrap.querySelectorAll('.lang-btn');
  var enBody = document.querySelector('[data-lang-body="en"]');
  var bnBody = document.querySelector('[data-lang-body="bn"]');
  if (!enBody || !bnBody) return;

  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      var lang = b.getAttribute('data-lang-body');
      btns.forEach(function (x) { x.classList.toggle('active', x === b); });
      var showBn = lang === 'bn';
      enBody.hidden = showBn;
      bnBody.hidden = !showBn;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
})();