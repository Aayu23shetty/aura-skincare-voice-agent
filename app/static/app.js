const $ = (id) => document.getElementById(id);

let active = false;
let transcript = [];
let recognition = null;
let speaking = false;
let manualStop = false;
let callStartedAt = null;

const stateLabel = $("stateLabel");
const stateDot = $("stateDot");
const orb = $("orb");
const startBtn = $("startBtn");
const endBtn = $("endBtn");
const transcriptEl = $("transcript");
const summaryPanel = $("summaryPanel");
const summaryJson = $("summaryJson");
const modePill = $("modePill");
const micNote = $("micNote");

function setState(state) {
  stateLabel.textContent = state;
  orb.classList.toggle("active", state === "Listening" || state === "Speaking");
  orb.classList.toggle("thinking", state === "Thinking");
  const dotColors = {Listening:"#789a7e", Thinking:"#c4a76b", Speaking:"#536e59", Idle:"#b5bdb7"};
  stateDot.style.background = dotColors[state] || dotColors.Idle;
}

function renderTranscript() {
  if (!transcript.length) {
    transcriptEl.innerHTML = `<div class="empty"><div class="empty-icon">◌</div><p>Your live transcript will appear here.</p></div>`;
    return;
  }
  transcriptEl.innerHTML = transcript.map(t => `
    <div class="turn ${t.speaker === "customer" ? "customer" : "agent"}">
      <div class="avatar">${t.speaker === "customer" ? "YOU" : "A"}</div>
      <div>
        <div class="speaker">${t.speaker}</div>
        <div class="bubble">${escapeHtml(t.text)}</div>
      </div>
    </div>
  `).join("");
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

async function checkHealth() {
  try {
    const r = await fetch("/api/health");
    const data = await r.json();
    modePill.textContent = data.mode === "ai" ? "AI mode · API connected" : "Demo mode · no API key";
  } catch {
    modePill.textContent = "Offline";
  }
}

function browserVoice() {
  const voices = speechSynthesis.getVoices();
  return voices.find(v => /en-IN/i.test(v.lang)) ||
         voices.find(v => /India/i.test(v.name)) ||
         voices.find(v => /en-GB/i.test(v.lang)) ||
         voices[0];
}

function speak(text) {
  return new Promise(resolve => {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = browserVoice();
    if (voice) utterance.voice = voice;
    utterance.lang = voice?.lang || "en-IN";
    utterance.rate = 0.98;
    utterance.pitch = 1.02;
    utterance.onstart = () => { speaking = true; setState("Speaking"); };
    utterance.onend = () => { speaking = false; resolve(); };
    utterance.onerror = () => { speaking = false; resolve(); };
    speechSynthesis.speak(utterance);
  });
}

async function askAgent(text) {
  if (!text.trim() || !active) return;
  transcript.push({speaker:"customer", text});
  renderTranscript();
  setState("Thinking");

  try {
    const r = await fetch("/api/chat", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({history: transcript.map(x => ({
        role: x.speaker === "customer" ? "user" : "assistant",
        content: x.text
      }))})
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || data.error || "Request failed");

    transcript.push({speaker:"agent", text:data.reply});
    renderTranscript();
    await speak(data.reply);
    if (active && !speaking) setState("Listening");
  } catch (err) {
    const fallback = "I'm sorry, I couldn't complete that request right now.";
    transcript.push({speaker:"agent", text:fallback});
    renderTranscript();
    await speak(fallback);
    setState("Listening");
    console.error(err);
  }
}

function setupRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    micNote.textContent = "Speech recognition unavailable";
    return null;
  }
  const r = new SR();
  r.lang = "en-IN";
  r.continuous = true;
  r.interimResults = false;
  r.maxAlternatives = 1;

  r.onstart = () => { if (active && !speaking) setState("Listening"); };
  r.onresult = async (event) => {
    const result = event.results[event.results.length - 1];
    if (!result.isFinal || !active || speaking) return;
    const text = result[0].transcript.trim();
    if (text) await askAgent(text);
  };
  r.onerror = (event) => {
    if (event.error === "not-allowed") {
      micNote.textContent = "Microphone permission denied";
    } else if (event.error !== "aborted") {
      micNote.textContent = `Mic: ${event.error}`;
    }
  };
  r.onend = () => {
    if (active && !manualStop && !speaking) {
      try { r.start(); } catch {}
    }
  };
  return r;
}

async function startCall() {
  if (active) return;
  active = true; manualStop = false; callStartedAt = Date.now();
  transcript = [];
  summaryPanel.classList.add("hidden");
  renderTranscript();
  startBtn.disabled = true; endBtn.disabled = false;
  setState("Listening");
  recognition = setupRecognition();
  if (recognition) {
    try { recognition.start(); } catch {}
  }
  await speak("Hi, I’m Aria from Aura Skincare. How can I help you today?");
  if (active && recognition) {
    try { recognition.start(); } catch {}
  }
}

async function endCall() {
  if (!active) return;
  active = false; manualStop = true;
  setState("Idle");
  startBtn.disabled = false; endBtn.disabled = true;
  if (recognition) { try { recognition.stop(); } catch {} }
  speechSynthesis.cancel();
  if (!transcript.length) return;

  try {
    const r = await fetch("/api/summary", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({transcript})
    });
    const data = await r.json();
    summaryJson.textContent = JSON.stringify(data, null, 2);
    summaryPanel.classList.remove("hidden");
  } catch (err) {
    console.error(err);
  }
}

startBtn.addEventListener("click", startCall);
endBtn.addEventListener("click", endCall);

$("clearBtn").addEventListener("click", () => {
  transcript = [];
  summaryPanel.classList.add("hidden");
  summaryJson.textContent = "";
  renderTranscript();
});

$("copySummary").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(summaryJson.textContent);
    $("copySummary").textContent = "Copied";
    setTimeout(() => $("copySummary").textContent = "Copy JSON", 1200);
  } catch {}
});

document.querySelectorAll(".order-card").forEach(card => {
  card.addEventListener("click", () => {
    const oid = card.dataset.order;
    const prompt = `Can you tell me the current status of order ${oid}?`;
    if (!active) {
      startCall().then(() => setTimeout(() => askAgent(prompt), 800));
    } else {
      askAgent(prompt);
    }
  });
});

document.querySelectorAll(".suggestion").forEach(btn => {
  btn.addEventListener("click", () => {
    const text = btn.dataset.say;
    if (!active) {
      startCall().then(() => setTimeout(() => askAgent(text), 800));
    } else {
      askAgent(text);
    }
  });
});

window.speechSynthesis?.addEventListener("voiceschanged", () => {});

checkHealth();
renderTranscript();
