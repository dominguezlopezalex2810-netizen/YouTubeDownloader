const $ = (id) => document.getElementById(id);
const state = { url: "", destination: "", quality: null, jobId: null, source: null, toastTimer: null };
const qualityLabels = {2160:"2160p",1440:"1440p",1080:"1080p",720:"720p",480:"480p",360:"360p",240:"240p",144:"144p"};

function setBusy(button, busy, label) {
  button.disabled = busy;
  if (label) button.querySelector("span") ? button.querySelector("span").textContent = label : button.textContent = label;
}
function showToast(message) {
  $("toast").textContent = message; $("toast").classList.add("visible");
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => $("toast").classList.remove("visible"), 4300);
}
async function api(path, options = {}) {
  const response = await fetch(path, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "No se pudo completar la operación.");
  return data;
}
function formatBytes(value) {
  if (value == null) return null;
  const units = ["B","KB","MB","GB"]; let size = value, i = 0;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(1)} ${units[i]}`;
}
function updateDownloadEnabled() { $("downloadButton").disabled = !(state.quality && state.destination); }
function selectQuality(value, button) {
  state.quality = value;
  document.querySelectorAll(".quality-button").forEach(el => el.classList.toggle("selected", el === button));
  $("audioFormatRow").classList.toggle("hidden", value !== "audio");
  updateDownloadEnabled();
}
function renderQualities(info) {
  const grid = $("qualityGrid"); grid.innerHTML = "";
  info.resolutions.forEach(height => {
    const button = document.createElement("button"); button.type = "button"; button.className = "quality-button";
    button.innerHTML = `${qualityLabels[height] || height + "p"}${height === 2160 ? "<small>4K</small>" : ""}`;
    button.addEventListener("click", () => selectQuality(String(height), button)); grid.appendChild(button);
  });
  if (info.audio_available) {
    const button = document.createElement("button"); button.type = "button"; button.className = "quality-button";
    button.innerHTML = "Solo audio<small>M4A (AAC) / MP3</small>"; button.addEventListener("click", () => selectQuality("audio", button)); grid.appendChild(button);
  }
  const first = grid.querySelector(".quality-button"); if (first) first.click();
}
async function analyze() {
  const url = $("urlInput").value.trim();
  $("analyzeStatus").className = "inline-status";
  if (!url) { $("analyzeStatus").textContent = "Introduce una URL de YouTube."; $("analyzeStatus").classList.add("error"); return; }
  setBusy($("analyzeButton"), true, "Analizando..."); $("analyzeStatus").textContent = "Analizando vídeo...";
  try {
    const info = await api("/api/analyze", {method:"POST", body:JSON.stringify({url})});
    state.url = url; state.quality = null;
    $("thumbnail").src = info.thumbnail || ""; $("videoTitle").textContent = info.title;
    $("channel").textContent = info.channel; $("duration").textContent = info.duration_text;
    renderQualities(info); $("videoSection").classList.remove("hidden"); $("analyzeStatus").textContent = "";
    $("videoSection").scrollIntoView({behavior:"smooth", block:"start"});
  } catch (error) {
    $("analyzeStatus").textContent = error.message; $("analyzeStatus").classList.add("error");
  } finally { setBusy($("analyzeButton"), false, "Analizar vídeo"); }
}
async function chooseFolder() {
  try {
    const data = await api("/api/select-folder", {method:"POST", body:"{}"});
    if (data.path) { state.destination = data.path; $("folderPath").textContent = data.path; $("folderPath").title = data.path; updateDownloadEnabled(); }
  } catch (error) { showToast(error.message); }
}
function applyProgress(job) {
  $("statusText").textContent = job.status_text; $("percentText").textContent = `${Math.round(job.progress)}%`;
  $("progressBar").style.width = `${job.progress}%`; $("speedText").textContent = job.speed || "—";
  $("filenameText").textContent = job.filename || "Preparando archivo";
  const down = formatBytes(job.downloaded), total = formatBytes(job.total);
  $("sizeText").textContent = down ? `${down}${total ? " / " + total : " descargados"}` : "Calculando tamaño...";
  if (job.finished) {
    state.source?.close(); state.source = null; $("cancelButton").classList.add("hidden");
    $("downloadButton").disabled = false;
    if (job.status === "completed") { $("openFolderButton").classList.remove("hidden"); $("sizeText").textContent = "Archivo guardado correctamente"; }
    else if (job.status === "error") showToast(job.error || "La descarga no pudo completarse.");
  }
}
async function startDownload() {
  if (!state.quality || !state.destination) return;
  $("progressSection").classList.remove("hidden"); $("cancelButton").classList.remove("hidden"); $("openFolderButton").classList.add("hidden");
  $("downloadButton").disabled = true; applyProgress({status_text:"Preparando descarga...",progress:0,speed:null,downloaded:null,total:null,filename:null,finished:false});
  try {
    const job = await api("/api/downloads", {method:"POST", body:JSON.stringify({url:state.url,quality:state.quality,audio_format:$("audioFormat").value,destination:state.destination})});
    state.jobId = job.id; state.source = new EventSource(`/api/downloads/${job.id}/events`);
    state.source.onmessage = event => applyProgress(JSON.parse(event.data));
    state.source.onerror = () => { if (state.source) { state.source.close(); state.source = null; showToast("Se perdió la conexión con el progreso de la descarga."); } };
    $("progressSection").scrollIntoView({behavior:"smooth", block:"nearest"});
  } catch (error) { $("downloadButton").disabled = false; showToast(error.message); }
}
async function cancelDownload() {
  if (!state.jobId) return; $("cancelButton").disabled = true;
  try { await api(`/api/downloads/${state.jobId}/cancel`, {method:"POST", body:"{}"}); }
  catch (error) { showToast(error.message); }
  finally { $("cancelButton").disabled = false; }
}

$("analyzeButton").addEventListener("click", analyze);
$("urlInput").addEventListener("keydown", e => { if (e.key === "Enter") analyze(); });
$("urlInput").addEventListener("input", e => $("clearUrl").classList.toggle("hidden", !e.target.value));
$("clearUrl").addEventListener("click", () => { $("urlInput").value = ""; $("clearUrl").classList.add("hidden"); $("urlInput").focus(); });
$("folderButton").addEventListener("click", chooseFolder); $("downloadButton").addEventListener("click", startDownload); $("cancelButton").addEventListener("click", cancelDownload);
$("openFolderButton").addEventListener("click", () => api("/api/open-folder", {method:"POST",body:JSON.stringify({path:state.destination})}).catch(e => showToast(e.message)));
$("themeButton").addEventListener("click", () => { const dark = document.documentElement.dataset.theme === "dark"; document.documentElement.dataset.theme = dark ? "light" : "dark"; localStorage.setItem("theme", dark ? "light" : "dark"); });
document.documentElement.dataset.theme = localStorage.getItem("theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
