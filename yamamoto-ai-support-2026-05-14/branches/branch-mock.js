(function () {
  const config = window.branchMockConfig;
  if (!config) return;

  const state = {
    activeOutput: config.outputs[0].id,
    generatedAt: "未生成"
  };

  const nav = [
    ["01", "月次報告", "01_monthly-report.html"],
    ["02", "衛生委員会", "02_safety-committee.html"],
    ["03", "面談準備", "03_interview-checklist.html"],
    ["04", "提案書", "04_service-proposal.html"],
    ["05", "事務ひな形", "05_admin-templates.html"],
    ["06", "会議録", "06_meeting-minutes.html"],
    ["07", "支援先管理", "07_client-hub.html"]
  ];

  const s = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const nl = (value) => s(value).replace(/\n/g, "<br>");
  const byId = (id) => document.getElementById(id);

  function setupText() {
    byId("page-eyebrow").textContent = config.eyebrow;
    byId("page-title").textContent = config.title;
    byId("page-lead").textContent = config.lead;
    byId("status-strong").textContent = config.statusTitle;
    byId("status-copy").textContent = config.statusCopy;
    byId("control-title").textContent = config.controlTitle;
    byId("control-copy").textContent = config.controlCopy;
    byId("safety-copy").textContent = config.safety;
    document.title = config.documentTitle;
  }

  function setupNav() {
    byId("branch-nav").innerHTML = nav.map(([num, label, href]) => {
      const current = num === config.current;
      return `<a class="${current ? "is-current" : ""}" href="./${href}">${s(label)}</a>`;
    }).join("");
  }

  function setupImpact() {
    const cards = config.impactCards || [];
    const flow = config.demoFlow || [];
    if (!cards.length && !flow.length) return;

    const navEl = byId("branch-nav");
    const section = document.createElement("section");
    section.className = "impact-zone";

    const cardHtml = cards.length
      ? `<div class="impact-grid">${cards.map((card) => `
          <article class="impact-card ${s(card.tone || "")}">
            <span>${s(card.label)}</span>
            <strong>${s(card.title)}</strong>
            <p>${s(card.copy)}</p>
          </article>
        `).join("")}</div>`
      : "";

    const flowHtml = flow.length
      ? `<div class="flow-strip">${flow.map((item, index) => `
          <div class="flow-step">
            <span>${String(index + 1).padStart(2, "0")}</span>
            <strong>${s(item.title)}</strong>
            <p>${s(item.copy)}</p>
          </div>
        `).join("")}</div>`
      : "";

    section.innerHTML = `${cardHtml}${flowHtml}`;
    navEl.insertAdjacentElement("afterend", section);
  }

  function setupFields() {
    byId("mock-fields").innerHTML = config.fields.map((field) => {
      const value = s(field.value);
      const helper = field.helper ? `<small>${s(field.helper)}</small>` : "";
      if (field.type === "textarea") {
        return `<div class="field">
          <label for="${s(field.id)}">${s(field.label)}</label>
          <textarea id="${s(field.id)}" data-field="${s(field.id)}">${value}</textarea>
          ${helper}
        </div>`;
      }
      if (field.type === "select") {
        const options = field.options.map((option) => {
          const selected = option === field.value ? " selected" : "";
          return `<option${selected}>${s(option)}</option>`;
        }).join("");
        return `<div class="field">
          <label for="${s(field.id)}">${s(field.label)}</label>
          <select id="${s(field.id)}" data-field="${s(field.id)}">${options}</select>
          ${helper}
        </div>`;
      }
      return `<div class="field">
        <label for="${s(field.id)}">${s(field.label)}</label>
        <input id="${s(field.id)}" data-field="${s(field.id)}" value="${value}">
        ${helper}
      </div>`;
    }).join("");

    document.querySelectorAll("[data-field]").forEach((element) => {
      element.addEventListener("input", renderPreview);
      element.addEventListener("change", renderPreview);
    });
  }

  function setupModes() {
    byId("mode-row").innerHTML = config.outputs.map((output) => (
      `<button class="mode-button" type="button" data-output="${s(output.id)}">${s(output.label)}</button>`
    )).join("");

    document.querySelectorAll("[data-output]").forEach((button) => {
      button.addEventListener("click", () => {
        state.activeOutput = button.dataset.output;
        renderPreview();
      });
    });
  }

  function readFields() {
    const values = {};
    document.querySelectorAll("[data-field]").forEach((element) => {
      values[element.dataset.field] = element.value;
    });
    return values;
  }

  function activeOutput() {
    return config.outputs.find((output) => output.id === state.activeOutput) || config.outputs[0];
  }

  function renderPreview() {
    const output = activeOutput();
    const values = readFields();

    document.querySelectorAll("[data-output]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.output === output.id);
    });

    byId("mode-desc").textContent = output.description;
    byId("preview").innerHTML = `
      <div class="preview-meta">
        <span class="tag blue">入力をもとに作る例</span>
        <span class="tag green">${s(output.label)}</span>
        <span class="tag amber">表示: ${s(state.generatedAt)}</span>
      </div>
      ${output.render(values, { s, nl })}
    `;
  }

  function setupButtons() {
    byId("generate-button").addEventListener("click", () => {
      const button = byId("generate-button");
      button.classList.add("is-generating");
      button.textContent = "下書き生成中";
      window.setTimeout(() => {
        state.generatedAt = new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
        button.classList.remove("is-generating");
        button.textContent = "下書きを作る";
        renderPreview();
      }, 360);
    });

    byId("reset-button").addEventListener("click", () => {
      config.fields.forEach((field) => {
        const element = byId(field.id);
        if (element) element.value = field.value;
      });
      state.generatedAt = "初期例";
      renderPreview();
    });
  }

  function setupInfo() {
    byId("fit-title").textContent = config.fitTitle;
    byId("fit-copy").textContent = config.fitCopy;
    byId("fit-list").innerHTML = config.fitList.map((item) => `<li>${s(item)}</li>`).join("");
    byId("questions-list").innerHTML = config.questions.map((item) => `<li>${s(item)}</li>`).join("");
    byId("next-step").innerHTML = config.nextStep;
  }

  setupText();
  setupNav();
  setupImpact();
  setupFields();
  setupModes();
  setupButtons();
  setupInfo();
  state.generatedAt = "初期例";
  renderPreview();
})();
