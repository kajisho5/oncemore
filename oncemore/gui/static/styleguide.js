// The style guide page (the app's CSP forbids inline scripts).
for (const box of document.querySelectorAll("[data-tokens]")) {
  box.innerHTML = box.dataset.tokens.split(" ").map((v) =>
    `<div class="sw"><i style="background:var(${v})"></i><code>${v}</code></div>`).join("");
}
document.getElementById("theme").onclick = () => {
  const r = document.documentElement;
  if (r.dataset.theme === "light") delete r.dataset.theme; else r.dataset.theme = "light";
};
