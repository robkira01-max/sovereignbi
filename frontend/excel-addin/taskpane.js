/* global Office, Excel */
"use strict";

let lastResults = null;

Office.onReady(function (info) {
  if (info.host === Office.HostType.Excel) {
    document.getElementById("btn-send").onclick = sendSheetData;
    document.getElementById("btn-ask").onclick = askQuestion;
    document.getElementById("btn-insert").onclick = insertResults;
    document.getElementById("btn-save-settings").onclick = saveSettings;
    loadSettings();
  }
});

function getApiBase() {
  return localStorage.getItem("sovereign_api_url") || "http://localhost:9000";
}

function getApiKey() {
  return localStorage.getItem("sovereign_api_key") || "";
}

function loadSettings() {
  const urlEl = document.getElementById("api-url");
  const keyEl = document.getElementById("api-key");
  if (urlEl) urlEl.value = getApiBase();
  if (keyEl) keyEl.value = getApiKey();
}

function saveSettings() {
  const url = document.getElementById("api-url").value.trim().replace(/\/$/, "");
  const key = document.getElementById("api-key").value.trim();
  localStorage.setItem("sovereign_api_url", url);
  localStorage.setItem("sovereign_api_key", key);
  showStatus("Paramètres sauvegardés.", "success");
}

function showStatus(msg, type) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status " + (type || "info");
}

function showResult(data) {
  const zone = document.getElementById("result-zone");
  if (!data || data.error) {
    zone.innerHTML = `<div class="error">${data ? data.error : "Aucun résultat."}</div>`;
    return;
  }
  let html = `<div class="answer">${data.answer || ""}</div>`;
  if (data.sql) {
    html += `<details><summary>SQL généré</summary><pre>${data.sql}</pre></details>`;
  }
  if (data.columns && data.rows && data.rows.length > 0) {
    html += "<table><thead><tr>";
    data.columns.forEach((c) => { html += `<th>${c}</th>`; });
    html += "</tr></thead><tbody>";
    data.rows.slice(0, 50).forEach((row) => {
      html += "<tr>";
      row.forEach((cell) => { html += `<td>${cell ?? ""}</td>`; });
      html += "</tr>";
    });
    html += "</tbody></table>";
    if (data.rows.length > 50) {
      html += `<p class="note">${data.rows.length} lignes — 50 affichées.</p>`;
    }
  }
  if (data.confidence_grade) {
    html += `<div class="grade">Confiance : <strong>${data.confidence_grade}</strong></div>`;
  }
  zone.innerHTML = html;
  lastResults = data;
  document.getElementById("btn-insert").disabled = false;
}

async function sendSheetData() {
  showStatus("Lecture de la feuille active...", "info");
  document.getElementById("btn-send").disabled = true;
  try {
    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      const range = sheet.getUsedRange();
      range.load(["values", "address"]);
      await context.sync();

      const values = range.values;
      if (!values || values.length < 2) {
        showStatus("La feuille est vide ou n'a qu'une ligne d'en-tête.", "error");
        return;
      }

      const columns = values[0].map((c) => String(c));
      const rows = values.slice(1).map((r) => r.map((v) => v === null ? "" : v));

      const payload = {
        sheet_name: sheet.name || "Feuil1",
        columns: columns,
        rows: rows,
        source: "excel-addin",
      };

      const resp = await fetch(`${getApiBase()}/api/v1/addin/push-data`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Api-Key": getApiKey(),
        },
        body: JSON.stringify(payload),
      });

      const data = await resp.json();
      if (!resp.ok) {
        showStatus(`Erreur : ${data.detail || resp.statusText}`, "error");
        return;
      }
      showStatus(
        `✅ Données envoyées — table "${data.table_name}" (${data.rows} lignes × ${data.columns} colonnes)`,
        "success"
      );
    });
  } catch (e) {
    showStatus(`Erreur Office.js : ${e.message}`, "error");
  } finally {
    document.getElementById("btn-send").disabled = false;
  }
}

async function askQuestion() {
  const question = document.getElementById("question").value.trim();
  if (!question) {
    showStatus("Entrez une question d'abord.", "error");
    return;
  }
  showStatus("Analyse en cours...", "info");
  document.getElementById("btn-ask").disabled = true;
  document.getElementById("result-zone").innerHTML = "";
  lastResults = null;
  document.getElementById("btn-insert").disabled = true;

  try {
    const resp = await fetch(`${getApiBase()}/api/v1/addin/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Api-Key": getApiKey(),
      },
      body: JSON.stringify({ question: question, context_loaded: true }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      showStatus(`Erreur : ${data.detail || resp.statusText}`, "error");
      return;
    }
    showStatus("Réponse reçue.", "success");
    showResult(data);
  } catch (e) {
    showStatus(`Erreur réseau : ${e.message}`, "error");
  } finally {
    document.getElementById("btn-ask").disabled = false;
  }
}

async function insertResults() {
  if (!lastResults || !lastResults.columns || !lastResults.rows) {
    showStatus("Aucun résultat à insérer.", "error");
    return;
  }
  try {
    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      const used = sheet.getUsedRange();
      used.load("rowCount");
      await context.sync();

      const startRow = used.rowCount + 2;
      const cols = lastResults.columns;
      const rows = lastResults.rows;
      const allData = [cols, ...rows];

      const insertRange = sheet.getRangeByIndexes(startRow, 0, allData.length, cols.length);
      insertRange.values = allData;
      await context.sync();

      showStatus(`✅ ${rows.length} lignes insérées à partir de la ligne ${startRow + 1}.`, "success");
    });
  } catch (e) {
    showStatus(`Erreur insertion : ${e.message}`, "error");
  }
}
