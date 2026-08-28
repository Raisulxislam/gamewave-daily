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
    timer = setInterval(function () { goto(current + 1); }, 7000);
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
  var h1 = document.querySelector('.x-title');
  if (!enBody || !bnBody) return;
  var lastFocused = null;

  function apply(lang) {
    var showBn = lang === 'bn';
    enBody.hidden = showBn;
    bnBody.hidden = !showBn;
    if (h1 && showBn && h1.dataset.bnTitle) {
      h1.textContent = h1.dataset.bnTitle;
      h1.classList.add('bn');
      document.documentElement.lang = 'bn';
    }
    if (h1 && !showBn) {
      h1.textContent = h1.dataset.enTitle;
      h1.classList.remove('bn');
      document.documentElement.lang = 'en';
    }
  }

  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      btns.forEach(function (x) { x.classList.toggle('active', x === b); });
      apply(b.getAttribute('data-lang-body'));
    });
  });

  btnWrap.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    var idx = Array.prototype.indexOf.call(btns, document.activeElement);
    if (idx < 0) return;
    e.preventDefault();
    var next = (e.key === 'ArrowRight') ? (idx + 1) % btns.length : (idx + btns.length - 1) % btns.length;
    btns[next].click();
    btns[next].focus();
  });
})();

(function () {
  var links = document.querySelectorAll('.nav a');
  var path = location.pathname;
  links.forEach(function (a) {
    var href = a.getAttribute('href') || '/';
    if (href !== '/' && path.indexOf(href) === 0) a.classList.add('active');
    if (href === '/' && path === '/') a.classList.add('active');
  });
})();