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
})();
