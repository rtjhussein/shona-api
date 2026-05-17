(function () {
  const root = document.documentElement;
  const toggle = document.querySelector("[data-theme-toggle]");
  const label = document.querySelector("[data-theme-label]");
  const storageKey = "shona-api.progress.theme";

  function applyTheme(theme) {
    const nextTheme = theme === "light" ? "light" : "dark";
    root.dataset.theme = nextTheme;
    if (toggle) {
      toggle.setAttribute("aria-pressed", String(nextTheme === "dark"));
    }
    if (label) {
      label.textContent = nextTheme === "dark" ? "Dark" : "Light";
    }
  }

  applyTheme(window.localStorage.getItem(storageKey) || "dark");

  if (!toggle) {
    return;
  }

  toggle.addEventListener("click", function () {
    const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
    window.localStorage.setItem(storageKey, nextTheme);
    applyTheme(nextTheme);
  });
})();
