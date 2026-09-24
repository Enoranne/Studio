(() => {
  const EA = {
    open: false,
    mediaDbId: null,
    tracks: [],
    transcript: null,
    view: null,
    lastResult: null,
    loadingMediaDbId: null,
  };

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function currentAgentMedia() {
    let m = typeof getMedia === "function" ? getMedia(selectedMedia) : null;
    if (m?.dbId) return m;
    const clip = (clips || []).find(x => x.id === selectedClip);
    if (clip?.mediaDbId) {
      return (media || []).find(x => x.dbId === clip.mediaDbId) || null;
    }
    if (clip?.mediaId) {
      m = typeof getMedia === "function" ? getMedia(clip.mediaId) : null;
      if (m?.dbId) return m;
    }
    return (media || []).find(x => x.dbId) || null;
  }

  function drawer() {
    return document.getElementById("editorialAgentDrawer");
  }

  function body() {
    return document.getElementById("editorialAgentBody");
  }

  function waveformHtml(samples) {
    if (!samples?.length) {
      return '<div class="hint">Waveform indisponible — analyser les pistes audio.</div>';
    }
    const step = Math.max(1, Math.ceil(samples.length / 120));
    const bars = samples.filter((_, i) => i % step === 0).map(v => {
      const h = Math.max(3, Math.min(100, Math.round(Number(v || 0) * 100)));
      return `<i style="height:${h}%"></i>`;
    }).join("");
    return `<div class="agent-waveform" aria-label="Waveform audio">${bars}</div>`;
  }

  function phraseHtml(p) {
    return `<button class="agent-phrase" data-start="${Number(p.start)}" data-end="${Number(p.end)}"
      onclick="editorialAgentSeek(${EA.mediaDbId},${Number(p.start)},${Number(p.end)})">
      <span>${fmt(Number(p.start))}–${fmt(Number(p.end))}</span>
      <strong>${esc(p.speaker_id || "S")}</strong>
      <em>${esc(p.text || "")}</em>
    </button>`;
  }

  function render() {
    const host = body();
    if (!host) return;
    const m = (media || []).find(x => x.dbId === EA.mediaDbId);
    const tracks = EA.tracks || [];
    const activeTrack = tracks.find(x => x.selected_for_transcription);
    const transcript = EA.transcript;
    const view = EA.view || {};
    const cuts = view.cut_candidates || {};
    const refs = view.targeted_references || [];
    const phrases = transcript?.phrases || view.transcript?.phrases || [];

    host.innerHTML = `
      <section class="agent-section">
        <div class="agent-title-row">
          <div><small>MEDIA</small><strong>${esc(m?.label || "Aucun rush")}</strong></div>
          <button class="btn tiny" onclick="refreshEditorialAgent()">Actualiser</button>
        </div>
        <div class="agent-policy">Suggestions uniquement · aucune coupe automatique · validation humaine obligatoire.</div>
      </section>

      <section class="agent-section">
        <div class="agent-title-row"><strong>1 · AUDIO TRACK INTELLIGENCE</strong>
          <button class="btn tiny" onclick="analyzeEditorialAudioTracks()">Analyser</button>
        </div>
        ${tracks.length ? `
          <div class="agent-track-list">
            ${tracks.map(t => `<label class="agent-track ${t.silent ? "warn" : ""}">
              <input type="radio" name="ea-track" value="${t.track_index}" ${t.selected_for_transcription ? "checked" : ""}>
              <span>#${t.track_index} · ${esc(t.title || t.codec || "audio")}</span>
              <small>${t.channels || "?"} ch · ${t.peak_dbfs == null ? "—" : Number(t.peak_dbfs).toFixed(1) + " dBFS"}${t.silent ? " · SILENCE" : ""}</small>
            </label>`).join("")}
          </div>
          <button class="btn" onclick="selectEditorialAudioTrack()">Choisir la piste de transcription</button>
        ` : '<div class="hint">Aucune analyse de pistes disponible.</div>'}
      </section>

      <section class="agent-section">
        <div class="agent-title-row"><strong>2–4 · TRANSCRIPT INTELLIGENCE</strong>
          <button class="btn tiny" onclick="transcribeEditorialMedia()">Transcrire</button>
        </div>
        <div class="agent-meta">${activeTrack ? `Piste #${activeTrack.track_index}` : "Piste non choisie"} · ${transcript?.language_code || "langue —"}</div>
        ${waveformHtml(view.waveform)}
        <div class="agent-signals">
          <span>Silences ${(cuts.silence || []).length}</span>
          <span>Fillers ${(cuts.filler || []).length}</span>
          <span>Reprises ${(cuts.retake || []).length}</span>
          <span>Réfs vision ${refs.length}</span>
        </div>
        <div class="agent-transcript" id="agentTranscript">
          ${phrases.length ? phrases.map(phraseHtml).join("") : '<div class="hint">Aucun transcript. La transcription externe n’est lancée qu’après consentement explicite.</div>'}
        </div>
      </section>

      <section class="agent-section">
        <strong>5 · AI TIMELINE VIEW</strong>
        ${m?.filmstripUrl ? `<img class="agent-filmstrip" src="${m.filmstripUrl}" alt="Filmstrip">` : '<div class="hint">Filmstrip non généré.</div>'}
        <div class="agent-reference-row">${refs.slice(0,12).map(r => `<span>${esc(r.tag)} · ${esc(r.quality || "")}</span>`).join("") || "Aucune référence ciblée"}</div>
      </section>

      <section class="agent-section">
        <div class="agent-title-row"><strong>6 · TAKE COMPARATOR</strong>
          <button class="btn tiny" onclick="compareEditorialTakes()">Comparer rushes transcrits</button>
        </div>
        <div id="agentCompareResult" class="hint">Les meilleures prises restent une décision humaine.</div>
      </section>

      <section class="agent-section">
        <strong>7–9 · STRATÉGIE → EDL VIRTUELLE → APPLY</strong>
        <textarea id="agentBrief" rows="3" placeholder="Ex. teaser 45 s, enfance intime, montée progressive, éviter les spoilers…"></textarea>
        <div class="agent-form-row">
          <label>Cible <input id="agentTarget" type="number" min="5" max="300" value="45"> s</label>
          <label>Spoiler max <input id="agentSpoiler" type="number" min="0" max="99" value="0"></label>
        </div>
        <div class="ins-actions">
          <button class="btn" onclick="draftEditorialStrategy()">Proposer stratégie</button>
          <button class="btn primary" onclick="createEditorialProposal()">Créer EDL virtuelle</button>
        </div>
        <div id="agentProposalResult" class="agent-result">${EA.lastResult || ""}</div>
      </section>

      <section class="agent-section">
        <strong>10 · RENDERED MASTER CRITIC</strong>
        <input id="agentRenderPath" placeholder="edits/teaser_30/V001/teaser_30_V001.mp4"
          value="${esc(activeVersion ? `edits/${activeEditName}/${activeVersion}/${activeEditName}_${activeVersion}.mp4` : "")}">
        <button class="btn" onclick="runEditorialMasterCritic()">Analyser le rendu</button>
        <div id="agentCriticResult" class="agent-result"></div>
      </section>

      <section class="agent-section">
        <div class="agent-title-row"><strong>RECETTE PISTE 0 · V0.26</strong>
          <div>
            <button class="btn tiny" onclick="runEditorialProductionRecipe(false)">État</button>
            <button class="btn tiny" onclick="runEditorialProductionRecipe(true)">Enregistrer</button>
          </div>
        </div>
        <div class="hint">Rapport non destructif : rushes → audio → transcript → candidats → AI Timeline → EDL → humain → Storyline → Tesseract → Critic.</div>
        <div id="agentProductionRecipeResult" class="agent-result"></div>
      </section>
    `;
    syncEditorialAgentTranscript();
  }

  async function loadMedia(dbId) {
    if (!backendConnected || !dbId) return;
    dbId = Number(dbId);
    if (EA.loadingMediaDbId === dbId) return;
    EA.loadingMediaDbId = dbId;
    EA.mediaDbId = dbId;
    body().innerHTML = '<div class="card"><h3>Editorial Agent</h3><p>Chargement…</p></div>';
    try {
      const [tracks, transcript, view] = await Promise.all([
        api(`/api/audio/${EA.mediaDbId}/tracks`),
        api(`/api/transcripts/${EA.mediaDbId}`),
        api(`/api/editorial-agent/timeline-view/${EA.mediaDbId}`),
      ]);
      EA.tracks = tracks.tracks || [];
      EA.transcript = transcript.active || null;
      EA.view = view || null;
      render();
    } catch (err) {
      EA.tracks = [];
      EA.transcript = null;
      EA.view = null;
      render();
      toast("Editorial Agent : " + err.message, true);
    } finally {
      EA.loadingMediaDbId = null;
    }
  }

  window.openEditorialAgent = async function() {
    if (!backendConnected) {
      toast("Backend local requis", true);
      return;
    }
    const m = currentAgentMedia();
    if (!m?.dbId) {
      toast("Sélectionne un rush vidéo du catalogue", true);
      return;
    }
    EA.open = true;
    drawer().hidden = false;
    await loadMedia(m.dbId);
  };

  window.closeEditorialAgent = function() {
    EA.open = false;
    if (drawer()) drawer().hidden = true;
  };

  window.refreshEditorialAgent = async function() {
    const m = currentAgentMedia();
    if (m?.dbId) await loadMedia(m.dbId);
  };

  window.analyzeEditorialAudioTracks = async function() {
    if (!EA.mediaDbId) return;
    try {
      const r = await api(`/api/audio/${EA.mediaDbId}/tracks/analyze`, {
        method: "POST",
        body: JSON.stringify({ force: false }),
      });
      EA.tracks = r.tracks || [];
      toast(`${EA.tracks.length} piste(s) audio analysée(s)`);
      await loadMedia(EA.mediaDbId);
    } catch (err) {
      toast("Analyse pistes : " + err.message, true);
    }
  };

  window.selectEditorialAudioTrack = async function() {
    const checked = document.querySelector('input[name="ea-track"]:checked');
    if (!checked) {
      toast("Choisis une piste audio", true);
      return;
    }
    try {
      await api(`/api/audio/${EA.mediaDbId}/tracks/select`, {
        method: "POST",
        body: JSON.stringify({ track_index: Number(checked.value) }),
      });
      toast("Piste de transcription enregistrée");
      await loadMedia(EA.mediaDbId);
    } catch (err) {
      toast("Sélection piste : " + err.message, true);
    }
  };

  window.transcribeEditorialMedia = async function() {
    if (!EA.mediaDbId) return;
    const ok = window.confirm(
      "Transcription externe : l’audio de la piste choisie sera envoyé à ElevenLabs Scribe. Continuer ?"
    );
    if (!ok) return;
    try {
      toast("Transcription en cours…");
      await api(`/api/transcripts/${EA.mediaDbId}/transcribe`, {
        method: "POST",
        body: JSON.stringify({
          allow_network: true,
          provider: "elevenlabs",
          model_id: "scribe_v2",
        }),
      });
      toast("Transcript créé");
      await loadMedia(EA.mediaDbId);
    } catch (err) {
      toast("Transcription : " + err.message, true);
    }
  };

  window.editorialAgentSeek = function(dbId, start, end) {
    const m = (media || []).find(x => x.dbId === Number(dbId));
    if (!m) return;
    selectedMedia = m.id;
    if (typeof renderMedia === "function") renderMedia();
    if (typeof setViewerMode === "function") setViewerMode("source");
    if (typeof previewMedia === "function") previewMedia(m.id);
    const v = document.getElementById("video");
    const seek = () => {
      try { v.currentTime = Number(start); } catch (_) {}
      syncEditorialAgentTranscript(Number(start), Number(dbId));
    };
    if (v.readyState >= 1) seek();
    else v.addEventListener("loadedmetadata", seek, { once: true });
  };

  function sourcePosition() {
    if (viewerMode === "source") {
      const m = typeof getMedia === "function" ? getMedia(selectedMedia) : null;
      if (!m?.dbId) return null;
      return { dbId: m.dbId, time: Number(document.getElementById("video")?.currentTime || 0) };
    }
    const clip = (clips || []).find(c =>
      c.track === "video" &&
      playhead >= Number(c.start) &&
      playhead < Number(c.start) + Number(c.duration)
    );
    if (!clip) return null;
    const m = clip.mediaDbId
      ? (media || []).find(x => x.dbId === clip.mediaDbId)
      : (typeof getMedia === "function" ? getMedia(clip.mediaId) : null);
    if (!m?.dbId) return null;
    return {
      dbId: m.dbId,
      time: Number(clip.sourceStart || 0) + (Number(playhead) - Number(clip.start)),
    };
  }

  window.syncEditorialAgentTranscript = function(forceTime, forceDbId) {
    if (!EA.open) return;
    const pos = forceTime == null
      ? sourcePosition()
      : { dbId: forceDbId || EA.mediaDbId, time: Number(forceTime) };
    if (!pos) return;
    if (Number(pos.dbId) !== Number(EA.mediaDbId)) {
      if (EA.loadingMediaDbId !== Number(pos.dbId)) {
        loadMedia(Number(pos.dbId));
      }
      return;
    }
    const phrase = (EA.transcript?.phrases || EA.view?.transcript?.phrases || []).find(
      p => pos.time >= Number(p.start) && pos.time <= Number(p.end)
    );
    document.querySelectorAll(".agent-phrase").forEach(el => {
      el.classList.toggle(
        "active",
        !!phrase &&
        Math.abs(Number(el.dataset.start) - Number(phrase.start)) < 0.001
      );
    });
    const active = document.querySelector(".agent-phrase.active");
    if (active) active.scrollIntoView({ block: "nearest" });
  };

  window.compareEditorialTakes = async function() {
    try {
      const ids = (media || []).map(x => x.dbId).filter(Boolean);
      const r = await api("/api/editorial-agent/compare-takes", {
        method: "POST",
        body: JSON.stringify({ media_ids: ids, threshold: 0.7, max_pairs: 20 }),
      });
      const host = document.getElementById("agentCompareResult");
      host.innerHTML = r.matches?.length
        ? r.matches.slice(0,10).map(x =>
          `<div class="agent-match"><strong>${Math.round(x.similarity * 100)}%</strong> ${esc(x.left.text)} ↔ ${esc(x.right.text)}</div>`
        ).join("")
        : "Aucune prise suffisamment proche.";
    } catch (err) {
      toast("Take Comparator : " + err.message, true);
    }
  };

  function proposalPayload() {
    return {
      edit_name: activeEditName,
      media_ids: (media || []).map(x => x.dbId).filter(Boolean),
      target_seconds: Number(document.getElementById("agentTarget")?.value || 45),
      max_spoiler: Number(document.getElementById("agentSpoiler")?.value || 0),
      brief: document.getElementById("agentBrief")?.value || "",
    };
  }

  window.draftEditorialStrategy = async function() {
    try {
      const r = await api("/api/editorial-agent/strategy", {
        method: "POST",
        body: JSON.stringify(proposalPayload()),
      });
      EA.lastResult = `<div class="card"><h3>Stratégie #${r.proposal_id}</h3><p>${esc(r.strategy_text)}</p></div>`;
      render();
    } catch (err) {
      toast("Stratégie : " + err.message, true);
    }
  };

  window.createEditorialProposal = async function() {
    try {
      const r = await api("/api/editorial-agent/proposals", {
        method: "POST",
        body: JSON.stringify(proposalPayload()),
      });
      EA.lastResult = `
        <div class="card agent-proposal-card">
          <h3>EDL virtuelle #${r.proposal_id}</h3>
          <p>${Number(r.actual_seconds).toFixed(1)} s · ${r.segments.length} segment(s)</p>
          <div class="agent-segments">${r.segments.map(s =>
            `<div><strong>${esc(s.media_title)}</strong> ${fmt(s.source_start)}–${fmt(s.source_end)}<br><small>${esc(s.quote || "")}</small></div>`
          ).join("")}</div>
          <div class="ins-actions">
            <button class="btn primary" onclick="applyEditorialProposal(${r.proposal_id})">Valider et appliquer</button>
            <button class="btn" onclick="rejectEditorialProposal(${r.proposal_id})">Rejeter</button>
          </div>
        </div>`;
      render();
      toast("EDL virtuelle créée · Storyline inchangée");
    } catch (err) {
      toast("EDL virtuelle : " + err.message, true);
    }
  };

  window.applyEditorialProposal = async function(id) {
    const ok = window.confirm(
      "Appliquer cette EDL à la Storyline ? Un checkpoint Undo sera créé avant toute modification."
    );
    if (!ok) return;
    try {
      const r = await api(`/api/editorial-agent/proposals/${id}/apply`, {
        method: "POST",
        body: JSON.stringify({ confirm: true }),
      });
      if (r.timeline) {
        hydrateTimeline(r.timeline);
        renderTracks();
        setPlayhead(0);
      }
      EA.lastResult = `<div class="card"><h3>Proposition #${id} appliquée</h3><p>Checkpoint créé · locks vérifiés.</p></div>`;
      render();
      toast("Proposition appliquée à la Storyline");
    } catch (err) {
      toast("Application refusée : " + err.message, true);
    }
  };

  window.rejectEditorialProposal = async function(id) {
    try {
      await api(`/api/editorial-agent/proposals/${id}/reject`, {
        method: "POST",
        body: "{}",
      });
      EA.lastResult = `<div class="card"><h3>Proposition #${id} rejetée</h3></div>`;
      render();
    } catch (err) {
      toast("Rejet : " + err.message, true);
    }
  };

  window.runEditorialMasterCritic = async function() {
    const path = document.getElementById("agentRenderPath")?.value?.trim();
    if (!path) {
      toast("Indique le chemin du rendu dans le projet", true);
      return;
    }
    try {
      const r = await api("/api/editorial-agent/master-critic", {
        method: "POST",
        body: JSON.stringify({
          edit_name: activeEditName,
          version_label: activeVersion || null,
          source_path: path,
        }),
      });
      const host = document.getElementById("agentCriticResult");
      host.innerHTML = `<div class="card"><h3>${esc(r.status)} · Critic #${r.report_id}</h3>
        ${(r.findings || []).map(f => `<p><strong>${esc(f.code)}</strong> · ${esc(f.message)}</p>`).join("")}
        <small>Diagnostic uniquement · revue humaine toujours requise.</small></div>`;
    } catch (err) {
      toast("Master Critic : " + err.message, true);
    }
  };

  window.runEditorialProductionRecipe = async function(save) {
    const host = document.getElementById("agentProductionRecipeResult");
    if (host) host.innerHTML = '<div class="hint">Analyse de la chaîne V0.26…</div>';
    try {
      let r;
      if (save) {
        r = await api("/api/editorial-production-run", {
          method: "POST",
          body: JSON.stringify({
            edit_name: activeEditName,
            version: activeVersion || null,
          }),
        });
        r = r.report || r;
      } else {
        const params = new URLSearchParams({ edit_name: activeEditName });
        if (activeVersion) params.set("version", activeVersion);
        r = await api(`/api/editorial-production-run?${params.toString()}`);
      }
      if (!host) return;
      const stages = (r.stages || []).map(s =>
        `<div class="agent-match"><strong>${esc(s.status)}</strong> · ${esc(s.id)}<br><small>${esc(s.message || "")}</small></div>`
      ).join("");
      host.innerHTML = `<div class="card">
        <h3>${esc(r.status || "—")}</h3>
        <p>${esc(r.next_action || "")}</p>
        <div class="agent-segments">${stages}</div>
        <small>Aucun PASS artistique automatique · validation humaine obligatoire.</small>
      </div>`;
      if (save) toast("Rapport de recette V0.26 enregistré");
    } catch (err) {
      if (host) host.innerHTML = "";
      toast("Recette V0.26 : " + err.message, true);
    }
  };

  const originalSetPlayhead = window.setPlayhead;
  if (typeof originalSetPlayhead === "function") {
    window.setPlayhead = function(t) {
      const result = originalSetPlayhead(t);
      if (EA.open) requestAnimationFrame(() => syncEditorialAgentTranscript());
      return result;
    };
  }
  const video = document.getElementById("video");
  if (video) {
    video.addEventListener("timeupdate", () => {
      if (EA.open && viewerMode === "source") syncEditorialAgentTranscript();
    });
  }
})();
