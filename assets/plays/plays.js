/* 日々、AIで遊んでます：サムネを押すとその場で再生（動画は見本集の mp4、YouTube は nocookie の埋め込み）。
   JS が無い時はリンクのまま作品のページへ行く。 */
(function () {
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest(".play-thumb[data-video], .play-thumb[data-yt]");
    if (!a || a.classList.contains("is-playing") || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
    ev.preventDefault();
    var media;
    if (a.dataset.video) {
      media = document.createElement("video");
      media.src = a.dataset.video;
      media.controls = true;
      media.autoplay = true;
      media.playsInline = true;
      media.preload = "auto";
    } else {
      media = document.createElement("iframe");
      media.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(a.dataset.yt) + "?autoplay=1&rel=0";
      media.title = a.getAttribute("aria-label") || "YouTube";
      media.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      media.allowFullscreen = true;
    }
    a.classList.add("is-playing");
    a.removeAttribute("href");
    a.appendChild(media);
  });
})();
