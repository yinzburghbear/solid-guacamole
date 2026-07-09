(function () {
  "use strict";

  const LIST_CLASS = "graphite-plugin-list";
  const DISABLED_CLASS = "graphite-plugin-disabled-row";

  function textOf(node) {
    return (node && node.textContent ? node.textContent : "").replace(/\s+/g, " ").trim();
  }

  function buttonTextMatches(row, pattern) {
    return Array.from(row.querySelectorAll("button, a.btn, .btn"))
      .some((button) => pattern.test(textOf(button)));
  }

  function isProbablyPluginsPage(settingsRoot) {
    const path = window.location.pathname.toLowerCase();
    if (path.includes("plugin")) return true;

    const text = textOf(settingsRoot).toLowerCase();
    return text.includes("installed plugins") ||
      text.includes("available plugins") ||
      text.includes("reload plugins");
  }

  function isDisabledPluginRow(row) {
    if (row.classList.contains("disabled") || row.matches("[aria-disabled='true']")) return true;
    if (row.querySelector("[aria-disabled='true'], .disabled")) return true;

    const uncheckedToggle = row.querySelector("input[type='checkbox']:not(:checked), input[type='radio']:not(:checked)");
    if (uncheckedToggle) return true;

    /* Installed disabled plugins generally expose an Enable action, while
       enabled ones expose Disable. Available plugins expose Install and are
       left alone. */
    if (buttonTextMatches(row, /^enable$/i) && !buttonTextMatches(row, /^disable$/i)) return true;

    return false;
  }

  function candidateRows(settingsRoot) {
    const rows = Array.from(settingsRoot.querySelectorAll(".setting-group"));
    if (rows.length) return rows;

    return Array.from(settingsRoot.querySelectorAll(".card, .list-group-item"))
      .filter((row) => /plugin|install|enable|disable|reload/i.test(textOf(row)));
  }

  function applyPluginOrdering() {
    const settingsRoot = document.querySelector("#settings-container");
    if (!settingsRoot || !isProbablyPluginsPage(settingsRoot)) return;

    const rows = candidateRows(settingsRoot);
    if (!rows.length) return;

    const parents = new Set();
    rows.forEach((row, index) => {
      const disabled = isDisabledPluginRow(row);
      row.classList.toggle(DISABLED_CLASS, disabled);
      row.style.order = String((disabled ? 10000 : 0) + index);
      if (row.parentElement) parents.add(row.parentElement);
    });

    parents.forEach((parent) => parent.classList.add(LIST_CLASS));
  }

  let pending = 0;
  function schedule() {
    window.clearTimeout(pending);
    pending = window.setTimeout(applyPluginOrdering, 120);
  }

  schedule();
  window.addEventListener("hashchange", schedule);
  window.addEventListener("popstate", schedule);

  if (window.PluginApi && window.PluginApi.Event && window.PluginApi.Event.addEventListener) {
    window.PluginApi.Event.addEventListener("stash:location", schedule);
  }

  new MutationObserver(schedule).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
