(() => {
  const WAKE_WORDS = ["көмекші", "көмекшім", "емші", "тапшы", "айтшы", "шашы", "айша", "наша", "үшін", "шын", "барша", "қазақша", "патша", "өтірікші", "көрші", "үшін", "көмекши", "көмек", "өмір күші", "көмек ші","көмек ши"];
  const AWAKE_TIMEOUT_MS = 10000;
  const VAD_HANG_MS = 500;
  const ENERGY_THR = 0.012;

  const statusEl = document.getElementById("status");
  const sttEl    = document.getElementById("last-stt");
  const answerEl = document.getElementById("answer");
  const audioEl  = document.getElementById("tts-audio");
  const orb      = document.getElementById("orb");

  /* =================== WOW-фон: концентрические волны + искры =================== */
  const wavesCanvas = document.getElementById("bg-waves");
  const wavesCtx = wavesCanvas.getContext?.("2d");
  const prefersReduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  let DPR = 1, W = 0, H = 0, CX = 0, CY = 0;
  let waveColor = hexToRgb(cssVar("--idle"));
  let targetColor = hexToRgb(cssVar("--idle"));
  let orbLevelValue = 0;
  let t0 = performance.now();

  const ripples = [];  // расширяющиеся кольца {r, life}
  const sparks  = [];  // искры/частицы

  function cssVar(name){
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#5f8cff";
  }
  function hexToRgb(hex){
    const m = hex.replace("#","").match(/.{1,2}/g);
    if(!m) return {r:95,g:140,b:255};
    const [r,g,b] = m.map(x => parseInt(x,16));
    return {r,g,b};
  }
  const lerp = (a,b,t) => a+(b-a)*t;
  const lerpC = (a,b,t)=>({r:lerp(a.r,b.r,t),g:lerp(a.g,b.g,t),b:lerp(a.b,b.b,t)});

  function resize(){
    if(!wavesCtx) return;
    DPR = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    W = wavesCanvas.width  = Math.floor(window.innerWidth * DPR);
    H = wavesCanvas.height = Math.floor(window.innerHeight * DPR);
    wavesCanvas.style.width  = window.innerWidth + "px";
    wavesCanvas.style.height = window.innerHeight + "px";
    wavesCtx.setTransform(1,0,0,1,0,0);
    wavesCtx.scale(DPR, DPR);
  }
  window.addEventListener("resize", resize, {passive:true});

  function readOrbCenter(){
    const r = orb.getBoundingClientRect();
    CX = (r.left + r.right)/2;
    CY = (r.top  + r.bottom)/2;
  }

  function triggerRipple(){
    ripples.push({ r: 18, life: 1.0 });
    if (ripples.length > 7) ripples.shift();
  }

  function burstSparks(n=70, speed=1.8){
    const r = orb.getBoundingClientRect();
    const cx = (r.left + r.right)/2, cy = (r.top + r.bottom)/2;
    for(let i=0;i<n;i++){
      const a = Math.random()*Math.PI*2;
      const v = (0.6 + Math.random()*0.6) * speed;
      sparks.push({
        x: cx, y: cy,
        vx: Math.cos(a)*v, vy: Math.sin(a)*v,
        life: 1.0, size: 1.2 + Math.random()*1.6
      });
    }
    if (sparks.length > 400) sparks.splice(0, sparks.length-400);
  }

  function drawScene(now){
    if (!wavesCtx) return;
    const ctx = wavesCtx;
    const t = (now - t0) / 1000;

    // Центр волн — РЕАЛЬНЫЙ центр шара (чтоб всё было ровно)
    readOrbCenter();

    // Плавное приближение цвета к целевому
    waveColor = lerpC(waveColor, targetColor, 0.06);

    // Прозрачная подложка
    ctx.clearRect(0,0, W/DPR, H/DPR);

    // Мягкое рад. сияние (фон вокруг шара)
    const rad = Math.max(W,H) / DPR;
    const g = ctx.createRadialGradient(CX, CY, 0, CX, CY, rad*0.9);
    g.addColorStop(0, `rgba(${waveColor.r|0},${waveColor.g|0},${waveColor.b|0},0.10)`);
    g.addColorStop(1, `rgba(0,0,0,0)`);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(CX, CY, rad*0.9, 0, Math.PI*2);
    ctx.fill();

    // Концентрические «дышащие» кольца
    const lvl = orbLevelValue;
    const baseAmp = 14 + 26*lvl; // шаг между кольцами
    const speed = 0.75 + 0.55*lvl; // скорость
    const rings = 6;

    ctx.lineWidth = 2;
    for(let i=0;i<rings;i++){
      const phase = (t*speed + i*0.5);
      const rr = 90 + i*baseAmp + Math.sin(phase)*6*(1+i*0.15); // небольшое дыхание радиуса
      const a = 0.18 - i*0.02 + 0.05*lvl;
      ctx.strokeStyle = `rgba(${waveColor.r|0},${waveColor.g|0},${waveColor.b|0},${Math.max(0,a).toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(CX, CY, rr, 0, Math.PI*2);
      ctx.stroke();
    }

    // Сплэш-кольца (на смене состояния/старте/ответе)
    for (let k = ripples.length-1; k >= 0; k--){
      ripples[k].r += 220 * 0.016;      // скорость расширения
      ripples[k].life -= 0.018;         // затухание
      const a = Math.max(0, 0.22 * ripples[k].life);
      if (a <= 0 || ripples[k].r > Math.max(W,H)) { ripples.splice(k,1); continue; }
      ctx.strokeStyle = `rgba(${waveColor.r|0},${waveColor.g|0},${waveColor.b|0},${a.toFixed(3)})`;
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(CX, CY, ripples[k].r, 0, Math.PI*2); ctx.stroke();
    }

    // Искры
    for (let i=sparks.length-1; i>=0; i--){
      const sp = sparks[i];
      sp.x += sp.vx; sp.y += sp.vy;
      sp.vx *= 0.985; sp.vy *= 0.985;
      sp.life -= 0.018;
      if (sp.life <= 0) { sparks.splice(i,1); continue; }
      const a = 0.45 * sp.life;
      ctx.fillStyle = `rgba(${waveColor.r|0},${waveColor.g|0},${waveColor.b|0},${a.toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, sp.size, 0, Math.PI*2);
      ctx.fill();
    }

    requestAnimationFrame(drawScene);
  }

  function setWaveState(s){
    if (s === "idle")      targetColor = hexToRgb(cssVar("--idle"));
    if (s === "listening") targetColor = hexToRgb(cssVar("--listening"));
    if (s === "speaking")  targetColor = hexToRgb(cssVar("--speaking"));
    triggerRipple();
  }

  /* =================== ORB <-> волны =================== */
  function setOrbState(s){ // 'idle' | 'listening' | 'speaking'
    if (!orb) return;
    orb.classList.remove("idle","listening","speaking");
    orb.classList.add(s);
    setWaveState(s);
  }
  function setOrbLevel(v){ // 0..1
    const c = Math.max(0, Math.min(1, v));
    orbLevelValue = c;
    if (orb) orb.style.setProperty("--level", c.toFixed(3));
  }

  /* =================== Речь/распознавание =================== */
  let audioCtx, analyser, srcNode, stream;
  let mediaRecorder = null;
  let lastSpeechTs = 0;
  let collecting = false;
  let awake = false;
  let awakeUntil = 0;
  let isSpeaking = false;
  let prevLevel = 0;

  const setStatus = t => statusEl && (statusEl.textContent = t);
  const setSTT = t => sttEl && (sttEl.textContent = t || "");
  const setAnswer = html => answerEl && (answerEl.innerHTML = html || "");

  function pickMime() {
    if (!window.MediaRecorder) return "";
    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) return "audio/webm;codecs=opus";
    if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus"))  return "audio/ogg;codecs=opus";
    if (MediaRecorder.isTypeSupported("audio/mp4"))              return "audio/mp4"; // Safari
    return "";
  }

  async function ensureAudioCtx() {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === "suspended") await audioCtx.resume();
      const b = audioCtx.createBuffer(1, 1, 22050);
      const s = audioCtx.createBufferSource(); s.buffer=b; s.connect(audioCtx.destination); s.start(0);
    } catch {}
  }

  function energyLevel() {
    const buf = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(buf);
    let sum=0; for (let i=0;i<buf.length;i++){ const v=(buf[i]-128)/128; sum+=v*v; }
    return Math.sqrt(sum/buf.length);
  }
  function normalizeEnergy(eng){
    const base = 0.005, span = 0.04;
    return Math.max(0, Math.min(1, (eng - base) / span));
  }
  function filenameForMime(m) {
    if (!m) return "chunk.webm";
    if (m.includes("webm")) return "chunk.webm";
    if (m.includes("ogg"))  return "chunk.ogg";
    if (m.includes("mp4"))  return "chunk.mp4";
    return "chunk.bin";
  }

  async function startLoop() {
    await ensureAudioCtx();
    srcNode = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 2048;
    srcNode.connect(analyser);

    const mime = pickMime();
    let recordedBlob = null;

    const startPhrase = () => {
      if (mediaRecorder && mediaRecorder.state === "recording") return;
      try { mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined); }
      catch (e) { setStatus("Brauzer MediaRecorder-dı qollamaydı. Chrome paydalanıń."); throw e; }
      recordedBlob = null;
      mediaRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) recordedBlob = e.data; };
      mediaRecorder.onstop = async () => {
        if (!recordedBlob || recordedBlob.size < 2000) return; // слишком коротко
        const fd = new FormData();
        fd.append("file", recordedBlob, filenameForMime(mediaRecorder.mimeType || mime));
        await handleUtterance(fd);
      };
      mediaRecorder.start();
    };
    const stopPhrase = () => { if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop(); };

    const loop = () => {
      const eng = energyLevel();
      const level = normalizeEnergy(eng);
      setOrbLevel(level);

      // маленькие искры при резком подъёме голоса
      if (!isSpeaking && level - prevLevel > 0.18) burstSparks(18, 1.2);
      prevLevel = level;

      const now = Date.now();
      const isLoud = eng > ENERGY_THR;

      if (!isSpeaking) setOrbState(isLoud ? "listening" : "idle");

      if (isLoud) { lastSpeechTs = now; if (!collecting) { collecting = true; startPhrase(); } }
      const silenceLong = now - lastSpeechTs > VAD_HANG_MS;
      if (collecting && silenceLong) { collecting = false; stopPhrase(); }

      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);

    setStatus('Tıńlaw: aytıń "көмекші" hám súrawıñızdı.');
    triggerRipple(); // стартовый сплэш
  }

  async function handleUtterance(fd){
    let sttText = "";
    try {
      const r = await fetch("/api/transcribe", { method:"POST", body: fd });
      const j = await r.json();
      sttText = (j.text || "").trim();
    } catch(e){ console.error(e); setStatus("Qáte: transcribe."); return; }
    if (!sttText) return;
    setSTT(sttText);

    const plain = sttText.toLowerCase();
    const hasWake = WAKE_WORDS.some(w => plain.startsWith(w+" ") || plain===w);

    if (!awake && hasWake) {
      awake = true; awakeUntil = Date.now() + AWAKE_TIMEOUT_MS;
      const q = sttText.replace(/^(көмекші|көмекши|көмек ші|көмек ши)\s*/i, "").trim();
      if (q) { await askText(q); awake=false; } else { await askText("__wake_ack__"); awake=false; }
      return;
    }
    if (awake) {
      if (Date.now() > awakeUntil) { awake=false; setStatus('Tıńlaw: aytıń "Hurliman"...'); return; }
      await askText(sttText); awake=false;
    }
  }

  async function askText(q){
    setStatus("Qıdıraw atır...");
    try{
      const r = await fetch("/api/ask-text", {
        method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ text:q })
      });
      const j = await r.json();

      if (j.audio_url) {
        audioEl.src = j.audio_url;
        try { await audioEl.play(); } catch(e){}
      }
      setAnswer(`<div class="ans-text">${j.screen_text || ""}</div>`);
      setStatus('Tıńlaw: aytıń "Hurliman" hám súrawıñızdı.');
    } catch(e){
      console.error(e); setStatus("Qáte: javap alıp bolmadı.");
    }
  }

  /* =================== Инициализация =================== */
  window.addEventListener("load", async () => {
    resize();
    if (wavesCtx && !prefersReduced) requestAnimationFrame(drawScene);

    // события плеера — режим speaking + экшен
    audioEl.addEventListener("play",  () => { isSpeaking = true;  setOrbState("speaking"); triggerRipple(); burstSparks(90, 2.0); });
    audioEl.addEventListener("ended", () => { isSpeaking = false; });
    audioEl.addEventListener("pause", () => { isSpeaking = false; });

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation:true, noiseSuppression:true, channelCount:1 },
        video:false
      });
      await startLoop();
    } catch (e) {
      console.error("getUserMedia error:", e);
      const msg = e?.name || e?.message || String(e);
      if (/NotAllowed|Permission/i.test(msg))      setStatus("Mikrofon ruxsatı qajet. Brauzerden ruxsat beriń.");
      else if (/NotFound|Devices/i.test(msg))      setStatus("Mikrofon tabılmadı. Qurılmanı tekseriń.");
      else if (/SecurityError/i.test(msg))         setStatus("Secure context qajet. URL: http://localhost:8000 paydalanıń.");
      else                                         setStatus("Mikrofon ashıwda qáte. Brauzer parametrlerin tekseriń.");
      setAnswer(
        `<ul class="hint-list">
           <li><b>Chrome/macOS:</b>  → System Settings → Privacy & Security → Microphone → Allow for Chrome.</li>
           <li><b>Chrome:</b> Site settings → Microphone → Allow for http://localhost:8000</li>
           <li><b>Safari:</b> Settings for This Website → Microphone: Allow.</li>
         </ul>`
      );
    }
  });

  /* =================== утилиты =================== */
  function setWavePalette(name){
    targetColor = hexToRgb(cssVar(name));
  }

})();
