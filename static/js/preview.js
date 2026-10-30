(() => {
  const data = JSON.parse(document.getElementById("preview-data").textContent);
  const language = document.getElementById("sim-language");
  const component = document.getElementById("sim-component");
  const warning = document.getElementById("sim-warning");
  const count = document.getElementById("char-count");
  const widgets = [...document.querySelectorAll("[data-demo]")];
  const outputs = [...document.querySelectorAll("[data-output]")];

  function update() {
    const text = data.texts[language.value] || "";
    outputs.forEach((element) => { element.textContent = text || "No translation available"; });
    widgets.forEach((element) => { element.hidden = element.dataset.demo !== component.value; });
    count.textContent = String(text.length);
    const exceedsCount = data.max_length && text.length > data.max_length;
    warning.classList.remove("warning-error", "warning-ok");
    requestAnimationFrame(() => {
      const active = document.querySelector(`[data-demo="${component.value}"] .fit-target`);
      const overflows = active && (active.scrollWidth > active.clientWidth + 1 || active.scrollHeight > active.clientHeight + 1);
      if (exceedsCount || overflows) {
        warning.textContent = exceedsCount ? `Length warning: ${text.length} characters exceeds the ${data.max_length}-character limit.` : "Visual overflow warning: text exceeds the simulated UI space.";
        warning.classList.add("warning-error");
      } else {
        warning.textContent = data.max_length ? `Fits the ${data.max_length}-character limit and simulated component.` : "No character limit set. Check the rendered fit in this simulated component.";
        warning.classList.add("warning-ok");
      }
    });
  }
  language.addEventListener("change", update);
  component.addEventListener("change", update);
  window.addEventListener("resize", update);
  update();
})();
