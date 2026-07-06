/* Theme boot: loaded as a blocking script in <head> so the theme applies
   before first paint (no light/dark flash). Kept outside app.js because the
   CSP is script-src 'self' — no inline scripts.
   mt_theme = "light" | "dark" | "auto" (auto follows the OS). */
(function () {
  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  function apply() {
    var pref = localStorage.getItem("mt_theme") || "auto";
    var dark = pref === "dark" || (pref === "auto" && mq.matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? "#171f26" : "#3f93b8";
  }
  mq.addEventListener("change", apply);
  window.__applyTheme = apply;
  apply();
  /* Topbar sun/moon button: toggles an explicit light/dark preference
     (the profile picker still offers "auto"). */
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("themeToggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var dark = document.documentElement.dataset.theme === "dark";
      localStorage.setItem("mt_theme", dark ? "light" : "dark");
      apply();
      // keep the profile picker in sync if it is on screen
      var pick = document.getElementById("themePick");
      if (pick) {
        var pref = localStorage.getItem("mt_theme");
        pick.querySelectorAll("[data-theme]").forEach(function (b) {
          b.classList.toggle("btn--ghost", b.dataset.theme !== pref);
        });
      }
    });
  });
})();
