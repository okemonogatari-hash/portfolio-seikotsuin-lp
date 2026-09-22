const toggle = document.querySelector('.menu-toggle');
const nav = document.getElementById('site-nav');
function closeNav() {
  toggle.setAttribute('aria-expanded', 'false');
  nav.classList.remove('open');
}
toggle.addEventListener('click', () => {
  const open = toggle.getAttribute('aria-expanded') !== 'true';
  toggle.setAttribute('aria-expanded', String(open));
  nav.classList.toggle('open', open);
});
nav.querySelectorAll('a').forEach(link => link.addEventListener('click', closeNav));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
    closeNav();
    toggle.focus();
  }
});

// Pause only this decorative scene. Re-entering the viewport respects the user's choice.
const motionScene = document.querySelector('.motion-scene');
const motionToggle = document.querySelector('.motion-toggle');
if (motionScene && motionToggle) {
  motionToggle.addEventListener('click', () => {
    const paused = motionScene.classList.toggle('motion-paused');
    motionToggle.setAttribute('aria-pressed', String(paused));
    motionToggle.innerHTML = paused ? '<span aria-hidden="true">▷</span> 動きを再開する' : '<span aria-hidden="true">Ⅱ</span> 動きを止める';
  });
  if ('IntersectionObserver' in window) {
    const motionObserver = new IntersectionObserver(([entry]) => {
      motionScene.classList.toggle('motion-offscreen', !entry.isIntersecting);
    }, {threshold: 0});
    motionObserver.observe(motionScene);
  }
}
