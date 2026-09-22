(() => {
  const scene = document.querySelector('.world-scene');
  if (!scene) return;
  const layers = [...scene.querySelectorAll('.parallax-layer')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(pointer: fine)');
  const control = document.querySelector('.motion-toggle');
  let frame = 0;
  const inactive = () => reduced.matches || scene.classList.contains('motion-paused') || scene.classList.contains('motion-offscreen');
  function reset() {
    cancelAnimationFrame(frame);
    scene.style.setProperty('--mx', '0px');
    scene.style.setProperty('--my', '0px');
  }
  scene.addEventListener('pointermove', event => {
    if (!fine.matches || inactive()) return;
    const rect = scene.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width - .5) * 26;
    const y = ((event.clientY - rect.top) / rect.height - .5) * 18;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      if (inactive()) return;
      scene.style.setProperty('--mx', `${x.toFixed(2)}px`);
      scene.style.setProperty('--my', `${y.toFixed(2)}px`);
    });
  });
  scene.addEventListener('pointerleave', () => { if (!inactive()) reset(); });
  control?.addEventListener('click', () => {
    cancelAnimationFrame(frame);
    if (scene.classList.contains('motion-paused')) {
      const transforms = layers.map(layer => getComputedStyle(layer).transform);
      layers.forEach((layer, i) => { layer.style.transform = transforms[i]; });
    } else {
      layers.forEach(layer => { layer.style.transform = ''; });
      reset();
    }
  });
  reduced.addEventListener('change', () => {
    layers.forEach(layer => { layer.style.transform = ''; });
    reset();
  });
})();
