/* ============================================================
   OCCASIONALLY DIVINE — game client
   Wires the real backend loop and drives all cinematic feedback.

   COST NOTE: this app runs on a paid LLM API. To avoid needless
   billed calls we (a) cache elder dossiers per session, (b) persist
   the current situation so a refresh re-renders instead of calling
   /generate_situation again, (c) reuse an existing active_council
   instead of re-triggering, and (d) lock during in-flight requests.
   ============================================================ */

// Same-origin when served by FastAPI; fall back to localhost when opened as a file.
const API_BASE = (location.protocol === 'file:') ? 'http://localhost:8000' : '';
const KINGDOM_ID = 1;
const SIT_KEY = 'od_situation_v1';

const state = {
    kingdom: null,
    situation: null,
    council: null,      // { debate, proposal, effect, memories } for the active council
    elders: [],
    busy: false,
    dossierCache: {},   // elder name -> dossier json (avoid re-billing)
    minorCards: [],     // 2-3 drawn per-parameter minor cards for this turn
    locked: { situation: null, minors: {} }, // committed choices: main intervention index + {param: optIdx}
};

// A turn is fully staged once the main response AND every drawn minor card are locked.
function resetLocked() { state.locked = { situation: null, minors: {} }; }

// Must match COUNCIL_UNREST_THRESHOLD in backend/services/utils.py.
const COUNCIL_UNREST_THRESHOLD = 70;

const STAT_KEYS = ['food', 'faith', 'unrest', 'morale', 'trust'];
// Which direction is "good" — used to colour deltas & effects correctly.
const GOOD_WHEN_UP = { food: true, faith: true, trust: true, unrest: false, morale: false };

const MOOD_COLORS = {
    Hopeful: '#86cf8f', Devoted: '#a487f0', Neutral: '#a08871',
    Fearful: '#6f9bc4', Angry: '#d75a52', Grieving: '#8a7d9c',
};
const ELDER_COLORS = {
    Rowan: '#7fbf87', Aldric: '#a487f0', Tomas: '#b1904f',
    Martha: '#d8ad4b', Elric: '#5bb0a8',
};

// ---------- tiny helpers ----------
const $ = (id) => document.getElementById(id);

async function api(path, opts) {
    const res = await fetch(API_BASE + path, opts);
    if (!res.ok) {
        let detail = res.statusText;
        try { detail = (await res.json()).detail || detail; } catch (e) {}
        const err = new Error(detail);
        err.status = res.status;
        throw err;
    }
    return res.json();
}
const postJSON = (path, body) => api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function elderColor(name) {
    if (ELDER_COLORS[name]) return ELDER_COLORS[name];
    let h = 0;
    for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
    return `hsl(${h}, 45%, 60%)`;
}
function moodColor(mood) { return MOOD_COLORS[mood] || MOOD_COLORS.Neutral; }
function initials(name) { return (name || '?').trim().charAt(0).toUpperCase(); }

// Word effect -> {sign, arrow, good} for a given stat
function effectMeta(stat, word) {
    const w = String(word || 'none').toLowerCase();
    if (w === 'none' || w === '') return null;
    const isUp = /boost|miracle|divine/.test(w);
    const isDown = /harm|catastrophe|apocalyptic/.test(w);
    if (!isUp && !isDown) return null;
    const sign = isUp ? 1 : -1;
    const good = (sign > 0) === !!GOOD_WHEN_UP[stat];
    return { sign, arrow: sign > 0 ? '▲' : '▼', good };
}

// Animated integer roll
function rollNumber(el, from, to, dur = 750) {
    from = Number(from) || 0; to = Number(to) || 0;
    if (from === to) { el.textContent = to; return; }
    const start = performance.now();
    function frame(now) {
        const t = Math.min(1, (now - start) / dur);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(from + (to - from) * eased);
        if (t < 1) requestAnimationFrame(frame);
        else el.textContent = to;
    }
    requestAnimationFrame(frame);
}

// Float a +N / -N chip above a stat
function showDelta(stat, value) {
    if (!value) return;
    const mount = $(`delta-${stat}`);
    if (!mount) return;
    const good = (value > 0) === !!GOOD_WHEN_UP[stat];
    const chip = document.createElement('div');
    chip.className = 'delta-chip ' + (good ? 'gain' : 'loss');
    chip.textContent = (value > 0 ? '+' : '') + value;
    mount.appendChild(chip);
    setTimeout(() => chip.remove(), 1900);
}

// ---------- shrine art ----------
function shrineSVG(level) {
    const flame = `<g class="shrine-flame"><path d="M32 14 C28 20 30 24 32 26 C34 24 36 20 32 14 Z" fill="#e6c479"><animate attributeName="opacity" values="0.7;1;0.7" dur="1.4s" repeatCount="indefinite"/></path></g>`;
    if (level >= 3) {
        return `<svg viewBox="0 0 64 72"><rect x="18" y="30" width="28" height="34" fill="#4a3527"/><polygon points="32,2 20,30 44,30" fill="#6b4b31"/><rect x="30" y="0" width="4" height="10" fill="#e6c479"/><circle cx="32" cy="40" r="6" fill="#a487f0" opacity="0.85"/><rect x="28" y="52" width="8" height="12" fill="#140d09"/></svg>`;
    }
    if (level >= 2) {
        return `<svg viewBox="0 0 64 72"><polygon points="14,30 50,30 32,16" fill="#6b4b31"/><rect x="16" y="30" width="6" height="30" fill="#5a4130"/><rect x="29" y="30" width="6" height="30" fill="#5a4130"/><rect x="42" y="30" width="6" height="30" fill="#5a4130"/><rect x="12" y="60" width="40" height="6" fill="#45311f"/>${flame}</svg>`;
    }
    return `<svg viewBox="0 0 64 72"><rect x="20" y="40" width="24" height="8" fill="#5a4130"/><rect x="24" y="48" width="16" height="14" fill="#45311f"/><rect x="18" y="36" width="28" height="6" fill="#6b4b31"/>${flame}</svg>`;
}

function realmMood(k) {
    if (!k) return 'The realm holds its breath.';
    if (k.realm_unrest >= 85) return 'Torches gather at the shrine. The mob stirs.';
    if (k.food < 25) return 'Hunger stalks every street. The granaries echo.';
    if (k.faith >= 85) return 'The faithful sing your name into the night.';
    if (k.current_morale >= 70) return 'A grey despair settles over the people.';
    if (k.realm_unrest >= 60) return 'Discontent ripples through the crowds.';
    if (k.trust_in_ruling_class < 30) return 'The people no longer trust their rulers.';
    return 'The realm holds its breath, awaiting your will.';
}

// ============================================================
//  RENDER
// ============================================================
function renderKingdom(k, opts = {}) {
    const prev = opts.prev;
    if (!k) return;

    // Plaque
    $('realm-name').textContent = k.name || 'The Realm';
    $('realm-time').textContent = `Year ${k.current_year} · ${k.current_season}`;
    const shrineNames = { 1: 'The Wooden Altar', 2: 'The Stone Temple', 3: 'The Cathedral of the Heavens' };
    $('realm-shrine').textContent = shrineNames[k.shrine_level] || 'The Wooden Altar';

    // Mana orb
    const maxMana = k.divine_influence_max || 100;
    const manaPct = Math.max(0, Math.min(100, (k.divine_influence / maxMana) * 100));
    rollNumber($('mana-val'), prev ? prev.divine_influence : k.divine_influence, k.divine_influence);
    $('mana-fill').style.height = manaPct + '%';
    $('mana-orb').classList.toggle('charged', manaPct > 66);

    // Stats + bars + deltas
    const disp = { food: k.food, faith: k.faith, unrest: k.realm_unrest, morale: k.current_morale, trust: k.trust_in_ruling_class };
    const prevDisp = prev ? { food: prev.food, faith: prev.faith, unrest: prev.realm_unrest, morale: prev.current_morale, trust: prev.trust_in_ruling_class } : null;
    STAT_KEYS.forEach((s) => {
        const val = disp[s] ?? 0;
        const from = prevDisp ? prevDisp[s] : val;
        rollNumber($(`stat-${s}`), from, val);
        $(`bar-${s}`).style.width = Math.max(0, Math.min(100, val)) + '%';
        const meter = document.querySelector(`.stat-meter[data-stat="${s}"]`);
        const critical = (s === 'unrest' && val >= 75) || (s === 'food' && val < 25) || (s === 'morale' && val >= 75) || (s === 'faith' && val < 20);
        meter.classList.toggle('critical', critical);
        if (prevDisp) showDelta(s, val - prevDisp[s]);
    });

    // Realm banner
    $('shrine-emblem').innerHTML = shrineSVG(k.shrine_level || 1);
    $('realm-mood').textContent = realmMood(k);
    const dread = $('dread-fill');
    dread.style.width = Math.max(0, Math.min(100, k.realm_unrest)) + '%';
    dread.classList.toggle('near', k.realm_unrest >= COUNCIL_UNREST_THRESHOLD - 10);

    // Atmosphere
    if (window.Atmosphere) {
        window.Atmosphere.setWeather(k.weather || 'Clear');
        window.Atmosphere.setOmen(k.omen_active || 'None');
    }

    // Subtle danger vignette — only when the realm is truly imperiled (thresholds
    // set beyond the per-meter "critical" marks, so this reads as a whole-realm dread
    // rather than firing for a single stat dipping low).
    const dangerOverlay = $('danger-overlay');
    if (dangerOverlay) {
        const inPeril = k.realm_unrest >= 78 || k.food < 20 || k.current_morale >= 80 || k.faith < 15;
        dangerOverlay.classList.toggle('active', inPeril);
    }
}

function renderElders(elders) {
    const list = $('elders-list');
    list.innerHTML = '';
    (elders || []).forEach((e) => {
        const card = document.createElement('div');
        card.className = 'elder-card';
        const belief = e.belief_in_divine ?? 50;
        const dissenter = (e.times_dissented || 0) > (e.times_agreed || 0) && (e.times_dissented || 0) >= 2;
        card.innerHTML = `
            ${dissenter ? '<span class="elder-badge">Dissenter</span>' : ''}
            <div class="elder-card-top">
                <div class="elder-sigil" style="background:${elderColor(e.name)}">${initials(e.name)}</div>
                <div>
                    <div class="elder-name">${e.name}</div>
                    <div class="elder-role">${e.role || ''}</div>
                </div>
            </div>
            <div class="elder-mood-row"><span class="mood-dot" style="background:${moodColor(e.mood)}"></span>${e.mood || 'Neutral'} · Belief ${belief}%</div>
            <div class="elder-belief-bar"><div class="elder-belief-fill" style="width:${belief}%"></div></div>
            ${e.memorable_quote ? `<div class="elder-quote">“${e.memorable_quote}”</div>` : ''}
        `;
        card.addEventListener('click', () => showElderDossier(e));
        list.appendChild(card);
    });
}

function renderChronicle(entries) {
    const list = $('chronicle-list');
    list.innerHTML = '';
    if (!entries || entries.length === 0) {
        list.innerHTML = '<li class="chronicle-empty">No history has yet been written.</li>';
        return;
    }
    entries.slice(0, 6).forEach((c) => {
        const li = document.createElement('li');
        li.className = 'chronicle-entry';
        li.innerHTML = `<div class="chronicle-when">Year ${c.year} · ${c.season}</div><div class="chronicle-text">${c.summary || c.consequence || ''}</div>`;
        list.appendChild(li);
    });
}

function renderAdaptations(adaptations) {
    const list = $('adaptations-list');
    list.innerHTML = '';
    if (!adaptations || adaptations.length === 0) {
        list.innerHTML = '<li class="adapt-empty">The kingdom has learned nothing… yet.</li>';
        return;
    }
    adaptations.forEach((a) => {
        const name = a.display_name || a;
        const li = document.createElement('li');
        const span = document.createElement('span');
        span.className = 'adapt-name';
        span.textContent = name;
        const btn = document.createElement('button');
        btn.className = 'explain-btn';
        btn.textContent = 'Explain';
        btn.addEventListener('click', () => showAdaptationJourney(a));
        li.appendChild(span); li.appendChild(btn);
        list.appendChild(li);
    });
}

function renderRumors(rumors) {
    const list = $('rumors-list');
    list.innerHTML = '';
    if (!rumors || rumors.length === 0) {
        list.innerHTML = '<li class="rumors-empty">The streets are quiet.</li>';
        return;
    }
    rumors.slice(0, 6).forEach((r) => {
        const li = document.createElement('li');
        const paranoid = /divine|unseen|god|hand|power|curse|witch/i.test(r.content || '');
        li.className = 'rumor-item' + (paranoid ? ' paranoid' : '');
        const spread = Math.max(0, Math.min(100, r.spread || 0));
        li.innerHTML = `<span class="rumor-text">“${r.content}”</span><div class="rumor-spread"><div class="rumor-spread-fill" style="width:${spread}%"></div></div>`;
        list.appendChild(li);
    });
}

let typewriterTimer = null;
function typewriter(el, text, done) {
    clearInterval(typewriterTimer);
    el.classList.add('typewriter-caret');
    el.textContent = '';
    let i = 0;
    const speed = text.length > 400 ? 8 : 14;
    typewriterTimer = setInterval(() => {
        el.textContent = text.slice(0, i);
        i += 2;
        if (i >= text.length) {
            clearInterval(typewriterTimer);
            el.textContent = text;
            el.classList.remove('typewriter-caret');
            el.classList.add('dropcap');
            if (done) done();
        }
    }, speed);
}

function renderSituation(sit) {
    state.situation = sit;
    const modal = $('situation-modal');
    modal.className = 'situation-modal sev-' + (sit.severity || 1);

    $('situation-category').textContent = sit.category || 'Event';
    const sev = $('situation-severity');
    sev.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
        const pip = document.createElement('span');
        pip.className = 'sev-pip' + (i <= (sit.severity || 1) ? ' on' : '');
        sev.appendChild(pip);
    }
    $('situation-title').textContent = sit.title || 'A Strange Season';

    // Causal-chain badge: this crisis grew out of a past one (Cognee + parent link).
    const badge = $('consequence-badge');
    if (sit.parent_situation_id && sit.parent_situation_title) {
        $('consequence-parent-title').textContent = `"${sit.parent_situation_title}"`;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }

    const narrative = $('situation-narrative');
    narrative.classList.remove('dropcap');
    typewriter(narrative, sit.narrative || '');

    renderMemoryEchoes(sit.retrieved_memories || []);
    renderInterventions(sit.interventions || []);
    renderMinorCards();
    updateProceed();
}

// Shows the raw Cognee graph memories that fed into this situation's generation,
// so the player can see the kingdom's knowledge graph actually working rather
// than trusting it silently happened.
// Memories arrive as {track, text} objects (backend tags each chunk by its source track),
// but old saves may still hold plain strings — normalize either shape.
const ECHO_MAX_CHARS = 180;
const ECHO_CAP = 8;

function echoParts(m) {
    if (m && typeof m === 'object') return { track: m.track || null, text: m.text || '' };
    return { track: null, text: m == null ? '' : String(m) };
}

function buildEchoLi(m) {
    const { track, text } = echoParts(m);
    const li = document.createElement('li');
    if (track) {
        const chip = document.createElement('span');
        chip.className = 'echo-track';
        chip.textContent = track;
        li.appendChild(chip);
    }
    const span = document.createElement('span');
    span.className = 'echo-text';
    const display = text.length > ECHO_MAX_CHARS ? text.slice(0, ECHO_MAX_CHARS).trimEnd() + '…' : text;
    span.textContent = display;
    if (display !== text) li.title = text;  // full chunk on hover when truncated
    li.appendChild(span);
    return li;
}

function renderMemoryEchoes(memories) {
    const panel = $('memory-echoes');
    const list = $('memory-echoes-list');
    const count = $('memory-echoes-count');
    list.innerHTML = '';

    if (!memories.length) {
        panel.hidden = true;
        return;
    }

    const shown = memories.slice(0, ECHO_CAP);
    count.textContent = '(' + shown.length + ')';
    shown.forEach((m) => list.appendChild(buildEchoLi(m)));
    panel.hidden = false;
    panel.open = true;  // open by default — judges see graph memory immediately
}

function renderInterventions(list) {
    const container = $('interventions-container');
    container.innerHTML = '';

    list.forEach((inv, index) => {
        const cost = inv.cost || 0;
        let kind = 'inert', tag = 'Forbearance';
        if (cost < 0) { kind = 'wrathful'; tag = 'Wrathful'; }
        else if (cost > 0) { kind = 'benevolent'; tag = 'Blessing'; }

        const card = document.createElement('div');
        card.className = 'intervention-card ' + kind;
        if (state.locked.situation === index) card.classList.add('selected');

        // effects
        const effs = inv.effects || {};
        let effHtml = '';
        STAT_KEYS.forEach((s) => {
            const key = s === 'unrest' ? 'unrest' : s;   // effects use food/faith/unrest/morale/trust
            const meta = effectMeta(s, effs[key]);
            if (meta) {
                const label = s === 'morale' ? 'Despair' : s.charAt(0).toUpperCase() + s.slice(1);
                effHtml += `<li><span>${label}</span><span class="${meta.good ? 'ic-eff-up' : 'ic-eff-down'}">${meta.arrow}</span></li>`;
            }
        });

        let costHtml, costClass;
        if (cost > 0) { costHtml = `✦ ${cost} Mana`; costClass = 'drain'; }
        else if (cost < 0) { costHtml = `✦ +${Math.abs(cost)} Mana (fear fuels you)`; costClass = 'gain'; }
        else { costHtml = 'No cost'; costClass = 'free'; }

        card.innerHTML = `
            <div class="ic-tag">${tag}</div>
            <div class="ic-desc">${inv.description || ''}</div>
            <div class="ic-cost ${costClass}">${costHtml}</div>
            <div class="ic-effects">
                <div class="ic-effect-title">Foreseen</div>
                <ul class="ic-effect-list">${effHtml || '<li><span>Uncertain</span></li>'}</ul>
            </div>`;

        card.addEventListener('click', () => selectIntervention(index));
        container.appendChild(card);
    });
}

// ---------- minor per-parameter cards (the "plan your season" commit layer) ----------
const MINOR_PARAM_LABEL = { food: 'Food', faith: 'Faith', unrest: 'Unrest', despair: 'Despair', trust: 'Trust' };

function renderMinorCards() {
    const section = $('minor-cards-section');
    const container = $('minor-cards-container');
    const cards = state.minorCards || [];
    container.innerHTML = '';

    if (!cards.length) { section.hidden = true; return; }
    section.hidden = false;

    cards.forEach((card) => {
        const param = card.param;
        const wrap = document.createElement('div');
        wrap.className = 'minor-card';

        const chosen = state.locked.minors[param];
        const opts = (card.options || []).map((opt, oi) => {
            // The card's delta acts on its own parameter; colour by whether that helps.
            const good = (opt.delta > 0) === !!GOOD_WHEN_UP[param === 'despair' ? 'morale' : param];
            let arrow = '';
            if (opt.delta > 0) arrow = `<span class="${good ? 'ic-eff-up' : 'ic-eff-down'}">▲${opt.delta}</span>`;
            else if (opt.delta < 0) arrow = `<span class="${good ? 'ic-eff-up' : 'ic-eff-down'}">▼${Math.abs(opt.delta)}</span>`;

            let mana;
            if (opt.cost > 0) mana = `<span class="minor-mana drain">✦ ${opt.cost}</span>`;
            else if (opt.cost < 0) mana = `<span class="minor-mana gain">✦ +${Math.abs(opt.cost)}</span>`;
            else mana = `<span class="minor-mana free">—</span>`;

            const sel = chosen === oi ? ' selected' : '';
            return `<button class="minor-option ${opt.kind}${sel}" data-param="${param}" data-oi="${oi}">
                        <span class="minor-opt-label">${opt.label}</span>
                        <span class="minor-opt-meta">${arrow}${mana}</span>
                    </button>`;
        }).join('');

        wrap.innerHTML = `
            <div class="minor-card-head">
                <span class="minor-param-tag">${MINOR_PARAM_LABEL[param] || param}</span>
                <span class="minor-card-title">${card.title || ''}</span>
            </div>
            <div class="minor-card-text">${card.text || ''}</div>
            <div class="minor-options">${opts}</div>`;

        wrap.querySelectorAll('.minor-option').forEach((btn) => {
            btn.addEventListener('click', () => selectMinorOption(btn.dataset.param, Number(btn.dataset.oi)));
        });
        container.appendChild(wrap);
    });
}

function selectIntervention(index) {
    if (state.busy) return;
    state.locked.situation = index;
    saveTurn();
    renderInterventions(state.situation.interventions || []);
    updateProceed();
}

function selectMinorOption(param, optIdx) {
    if (state.busy) return;
    state.locked.minors[param] = optIdx;
    saveTurn();
    renderMinorCards();
    updateProceed();
}

// Enable "Proceed" only once the main response and every minor card are chosen AND
// the whole plan's net mana cost is affordable. Mirrors the backend's net-cost gate.
function updateProceed() {
    const bar = $('proceed-bar');
    const btn = $('proceed-btn');
    const manaLabel = $('proceed-mana');
    const hint = $('proceed-hint');
    if (!state.situation) { bar.hidden = true; return; }
    bar.hidden = false;

    const mana = state.kingdom ? state.kingdom.divine_influence : 0;
    const cards = state.minorCards || [];
    const situationLocked = state.locked.situation !== null && state.locked.situation !== undefined;
    const allMinorsLocked = cards.every((c) => state.locked.minors[c.param] !== undefined);

    // Net cost = main intervention cost + every locked minor option's cost.
    let cost = 0;
    if (situationLocked) cost += (state.situation.interventions[state.locked.situation].cost || 0);
    cards.forEach((c) => {
        const oi = state.locked.minors[c.param];
        if (oi !== undefined) cost += (c.options[oi].cost || 0);
    });
    const projected = mana - cost;
    const affordable = projected >= 0;

    manaLabel.textContent = `Divine Influence: ${mana} → ${Math.max(0, projected)}`;
    manaLabel.classList.toggle('over', !affordable);

    const ready = situationLocked && allMinorsLocked && affordable && !state.busy;
    btn.disabled = !ready;

    if (!situationLocked) hint.textContent = 'Choose your divine response above.';
    else if (!allMinorsLocked) hint.textContent = 'Settle every lesser tremor to proceed.';
    else if (!affordable) hint.textContent = 'Not enough Divine Influence for this plan — let something feed your power.';
    else hint.textContent = 'The realm awaits your will.';
}

// ============================================================
//  GAME FLOW
// ============================================================
function showLoading(text) {
    $('loading-text').textContent = text || 'The threads of fate are weaving...';
    $('loading-overlay').classList.remove('hidden');
}
function hideLoading() { $('loading-overlay').classList.add('hidden'); }

async function loadWorld() {
    const data = await api('/world_state');
    state.kingdom = data.kingdom;
    state.elders = data.elders || [];
    renderKingdom(data.kingdom);
    renderElders(data.elders);
    renderChronicle(data.chronicle);
    renderAdaptations(data.kingdom.adaptations || data.adaptations);
    renderRumors(data.rumors);
    return data;
}

// Refresh panels + kingdom WITHOUT re-billing an LLM call, animating stat deltas.
async function syncWorld(prevKingdom) {
    const data = await api('/world_state');
    state.kingdom = data.kingdom;
    state.elders = data.elders || [];
    renderKingdom(data.kingdom, { prev: prevKingdom });
    renderElders(data.elders);
    renderChronicle(data.chronicle);
    renderAdaptations(data.kingdom.adaptations || data.adaptations);
    renderRumors(data.rumors);
    return data;
}

// Persist the whole in-progress turn (situation + drawn minor cards + locked choices)
// so a refresh restores it without re-billing a new generation.
function saveTurn() {
    if (!state.situation) return;
    localStorage.setItem(SIT_KEY, JSON.stringify({
        sit: state.situation,
        minorCards: state.minorCards,
        locked: state.locked,
    }));
}

// Raw fetch, no loading veil / rendering — lets callers start the (slow) generation
// call early and decide separately when/whether to show a spinner for it.
function fetchSituation() {
    return postJSON('/generate_situation');
}

function applySituationData(data) {
    state.minorCards = data.minor_cards || [];
    resetLocked();
    renderSituation(data.situation);   // reads state.minorCards / state.locked
    saveTurn();
}

async function generateSituation() {
    showLoading('The threads of fate are weaving...');
    try {
        const data = await fetchSituation();
        applySituationData(data);
    } catch (e) {
        showError('The Engine of History is silent. Is the backend running?', e);
    } finally {
        hideLoading();
    }
}

async function proceed() {
    if (state.busy || !state.situation) return;
    if (state.locked.situation === null || state.locked.situation === undefined) return;
    if (!(state.minorCards || []).every((c) => state.locked.minors[c.param] !== undefined)) return;
    state.busy = true;
    updateProceed(); // reflect the busy lock on the button
    const prevKingdom = state.kingdom;

    const index = state.locked.situation;
    const cost = state.situation.interventions[index].cost || 0;

    // Build minor_choices payload from the locked selections.
    const minor_choices = {};
    (state.minorCards || []).forEach((c) => {
        const oi = state.locked.minors[c.param];
        minor_choices[c.param] = { card_id: c.id, option_index: oi };
    });

    // Spectacle immediately (feels responsive), then clear the persisted turn
    // so a refresh mid-request can never replay the same choice.
    if (window.Atmosphere) {
        if (cost < 0) window.Atmosphere.playSpectacle('smite');
        else if (cost > 0) window.Atmosphere.playSpectacle('miracle');
        else window.Atmosphere.playSpectacle('nudge');
    }
    localStorage.removeItem(SIT_KEY);

    try {
        await sleep(650); // let the flash land
        showLoading('The season turns...');
        const result = await postJSON('/execute_intervention', {
            situation_id: state.situation.id,
            intervention_index: index,
            minor_choices,
        });
        hideLoading();

        // Prefetch the next situation now, in parallel with the player reading the
        // chronicle below — generation is the slow part, so starting it here (instead
        // of after they click Proceed) usually means it's already done by the time
        // it's needed, with no second loading veil. Only worth starting when we can
        // already tell the turn will actually continue (not ending / not off to council).
        let nextSituationPromise = null;
        let nextSituationSettled = false;
        const willContinue = (!result.kingdom.game_status || result.kingdom.game_status === 'active')
            && !result.council_summoned;
        if (willContinue) {
            nextSituationPromise = fetchSituation()
                .catch((e) => { console.error('[prefetch] situation generation failed', e); return null; })
                .finally(() => { nextSituationSettled = true; });
        }

        // 1) The epilogue — what the season wrought (+ adaptation save, if one fired)
        await showInterstitial(result.kingdom, result.epilogue, result.mitigated_by);

        // 2) Watch the numbers move, refresh the realm
        await syncWorld(prevKingdom);

        // 3) Endgame?
        if (result.kingdom.game_status && result.kingdom.game_status !== 'active') {
            state.busy = false;
            return showEndgame(result.kingdom.game_status);
        }

        // 4) Council convenes on max unrest, else the next crisis
        if (result.council_summoned) {
            state.busy = false;
            return runCouncil();
        }

        if (nextSituationPromise) {
            // Only show a loading veil if the prefetch genuinely hasn't finished yet —
            // most of the time the player's reading pace already covered it.
            if (!nextSituationSettled) showLoading('The threads of fate are weaving...');
            const data = await nextSituationPromise;
            hideLoading();
            if (data) applySituationData(data);
            else showError('The Engine of History is silent. Is the backend running?');
        } else {
            await generateSituation();
        }
    } catch (e) {
        hideLoading();
        showError('The divine will falters.', e);
    } finally {
        state.busy = false;
    }
}

let interstitialTimer = null;
function showInterstitial(kingdom, epilogue, mitigatedBy) {
    return new Promise((resolve) => {
        const saved = Array.isArray(mitigatedBy) && mitigatedBy.length > 0;
        if (!epilogue && !saved) return resolve();
        $('interstitial-plaque').textContent = `Year ${kingdom.current_year} · ${kingdom.current_season}`;

        // "The Kingdom Remembers" — a past Council adaptation just blunted this crisis.
        const banner = $('mitigation-banner');
        if (saved) {
            $('mitigation-text').textContent =
                `${mitigatedBy.join(' and ')} held firm — built for exactly this calamity. The damage is halved.`;
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }

        const overlay = $('interstitial-overlay');
        const epEl = $('interstitial-epilogue');
        const proceedBtn = $('interstitial-proceed');
        const text = epilogue || '';

        // Reset per-show state.
        clearInterval(interstitialTimer);
        epEl.classList.add('typewriter-caret');
        epEl.textContent = '';
        proceedBtn.classList.add('hidden');
        overlay.classList.remove('hidden');

        // Type the chronicle in so the player has time to read it, then reveal Proceed.
        let typing = true;
        const revealProceed = () => {
            typing = false;
            clearInterval(interstitialTimer);
            epEl.textContent = text;
            epEl.classList.remove('typewriter-caret');
            proceedBtn.classList.remove('hidden');
        };
        let i = 0;
        const speed = text.length > 400 ? 12 : 22;
        interstitialTimer = setInterval(() => {
            epEl.textContent = text.slice(0, i);
            i += 2;
            if (i >= text.length) revealProceed();
        }, speed);

        let done = false;
        const finish = () => {
            if (done) return; done = true;
            clearInterval(interstitialTimer);
            overlay.classList.add('hidden');
            overlay.removeEventListener('click', onOverlayClick);
            proceedBtn.removeEventListener('click', onProceed);
            resolve();
        };
        // Clicking the backdrop fast-forwards the typewriter; it never dismisses.
        const onOverlayClick = (e) => {
            if (e.target === proceedBtn) return;
            if (typing) revealProceed();
        };
        const onProceed = (e) => { e.stopPropagation(); finish(); };
        overlay.addEventListener('click', onOverlayClick);
        proceedBtn.addEventListener('click', onProceed);
    });
}

// ---------- Council ----------
function normalizeCouncil(d) {
    const md = d.discussion;
    const debate = Array.isArray(md) ? md : (md && md.discussion) || [];
    const proposal = d.proposal || (md && md.proposal) || 'An Adaptation';
    const effect = d.gameplay_effect_description || (md && md.gameplay_effect_description) || 'A new resilience for the realm.';
    const memories = d.retrieved_memories || [];
    return { debate, proposal, effect, memories };
}

let councilTimers = [];
function clearCouncilTimers() { councilTimers.forEach(clearTimeout); councilTimers = []; }

async function runCouncil(existing) {
    const overlay = $('council-overlay');
    $('council-decree').classList.add('hidden');
    $('council-debate').innerHTML = '';
    $('council-memory-list').innerHTML = '<li class="council-memory-empty">The elders search their memory...</li>';
    overlay.classList.remove('hidden');

    let data = existing;
    try {
        if (!data) {
            showLoading('The Council of Elders convenes...');
            data = await postJSON('/trigger_council');
            hideLoading();
        }
    } catch (e) {
        hideLoading();
        overlay.classList.add('hidden');
        return showError('The Council could not be summoned.', e);
    }

    const { debate, proposal, effect, memories } = normalizeCouncil(data);
    streamCouncil(debate, proposal, effect, memories);
}

function debateLineEl(line) {
    const speaker = line.speaker || line.name || 'Elder';
    const text = line.dialogue || line.text || '';
    const angry = /!|fool|never|traitor|blood|curse|refuse/i.test(text);
    const row = document.createElement('div');
    row.className = 'debate-line' + (angry ? ' angry' : '');
    row.innerHTML = `
        <div class="debate-sigil" style="background:${elderColor(speaker)}">${initials(speaker)}</div>
        <div class="debate-bubble">
            <div class="debate-speaker">${speaker}</div>
            <div class="debate-text">${text}</div>
        </div>`;
    return { row, angry };
}

function streamCouncil(debate, proposal, effect, memories) {
    clearCouncilTimers();
    state.council = { debate, proposal, effect, memories };
    const memList = $('council-memory-list');
    const debateBox = $('council-debate');
    memList.innerHTML = '';
    debateBox.innerHTML = '';

    // Reveal recalled memories (the knowledge graph made visible)
    if (!memories || memories.length === 0) {
        memList.innerHTML = '<li class="council-memory-empty">No deep memories stirred.</li>';
    } else {
        memories.slice(0, ECHO_CAP).forEach((m, i) => {
            councilTimers.push(setTimeout(() => {
                const li = buildEchoLi(m);
                li.style.animationDelay = '0s';
                memList.appendChild(li);
            }, 400 + i * 500));
        });
    }

    // Stream the debate line by line
    const startDelay = 600;
    const perLine = 1700;
    debate.forEach((line, i) => {
        councilTimers.push(setTimeout(() => {
            const { row, angry } = debateLineEl(line);
            debateBox.appendChild(row);
            debateBox.scrollTop = debateBox.scrollHeight;
            if (angry) {
                document.body.classList.add('shake-screen');
                setTimeout(() => document.body.classList.remove('shake-screen'), 500);
            }
        }, startDelay + i * perLine));
    });

    // Reveal the decree at the end
    councilTimers.push(setTimeout(() => revealDecree(proposal, effect),
        startDelay + debate.length * perLine + 300));
}

function revealDecree(proposal, effect) {
    $('decree-proposal').textContent = proposal;
    $('decree-effect').textContent = effect;
    const stamp = $('decree-stamp-btn');
    stamp.disabled = false;
    stamp.innerHTML = '<span class="seal">✹</span> Grant the Divine Seal';
    $('council-decree').classList.remove('hidden');
}

function skipCouncil() {
    // Fast-forward: render the whole debate + memories at once, then the decree.
    clearCouncilTimers();
    const c = state.council;
    if (!c) return;

    const memList = $('council-memory-list');
    memList.innerHTML = '';
    if (!c.memories || c.memories.length === 0) {
        memList.innerHTML = '<li class="council-memory-empty">No deep memories stirred.</li>';
    } else {
        c.memories.slice(0, ECHO_CAP).forEach((m) => {
            const li = buildEchoLi(m);
            li.style.animation = 'none'; li.style.opacity = '1'; li.style.transform = 'none';
            memList.appendChild(li);
        });
    }

    const debateBox = $('council-debate');
    debateBox.innerHTML = '';
    c.debate.forEach((line) => {
        const { row } = debateLineEl(line);
        row.style.animation = 'none'; row.style.opacity = '1'; row.style.transform = 'none';
        debateBox.appendChild(row);
    });
    debateBox.scrollTop = debateBox.scrollHeight;

    revealDecree(c.proposal, c.effect);
}

async function resolveCouncil() {
    if (state.busy) return;
    state.busy = true;
    const stamp = $('decree-stamp-btn');
    stamp.disabled = true;
    stamp.innerHTML = '<span class="seal">✹</span> Sealing...';
    const prevKingdom = state.kingdom;
    try {
        const result = await postJSON('/resolve_council');
        clearCouncilTimers();
        $('council-overlay').classList.add('hidden');
        if (window.Atmosphere) window.Atmosphere.playSpectacle('miracle');

        await syncWorld(prevKingdom);

        if (result.kingdom.game_status && result.kingdom.game_status !== 'active') {
            state.busy = false;
            return showEndgame(result.kingdom.game_status);
        }
        state.busy = false;
        await generateSituation();
    } catch (e) {
        showError('The seal would not hold.', e);
        state.busy = false;
    }
}

// ---------- Endgame ----------
function showEndgame(status) {
    const overlay = $('endgame-overlay');
    overlay.className = 'endgame-overlay ' + status;
    if (status === 'victory') {
        $('endgame-title').textContent = 'Ascension';
        $('endgame-text').textContent = 'Faith beyond mortal measure raises the Cathedral of the Heavens. Divine light pierces the clouds — you are no longer bound by mortal constraints. The kingdom remembers you as a god.';
    } else {
        $('endgame-title').textContent = 'The Shrine Burns';
        $('endgame-text').textContent = 'Unrest boiled over and faith ran dry. The mob took up torches and tore down the shrine. You are forgotten — a strange season the survivors will barely recall.';
    }
    overlay.classList.remove('hidden');
}

async function restartGame() {
    showLoading('A new age dawns...');
    try {
        await postJSON('/reset');
        localStorage.removeItem(SIT_KEY);
        state.dossierCache = {};
        $('endgame-overlay').classList.add('hidden');
        await loadWorld();
        await generateSituation();
    } catch (e) {
        showError('The world would not begin anew.', e);
    } finally {
        hideLoading();
    }
}

function showError(msg, e) {
    console.error(msg, e);
    $('situation-title').textContent = 'The Divine Connection Wavers';
    $('situation-narrative').classList.remove('dropcap');
    $('situation-narrative').textContent = `${msg} ${e && e.message ? '(' + e.message + ')' : ''} — start the backend with "python main.py" in the backend folder, then reload.`;
    $('interventions-container').innerHTML = '';
}

// ============================================================
//  MODALS (dossier / oracle / tapestry / lore / adaptation)
// ============================================================
async function showElderDossier(elder) {
    const modal = $('dossier-modal');
    modal.classList.remove('hidden');

    // Header fills instantly from data we already have
    $('dossier-avatar').textContent = initials(elder.name);
    $('dossier-avatar').style.background = elderColor(elder.name);
    $('dossier-name').textContent = elder.name;
    $('dossier-role').textContent = elder.role || '';
    $('dossier-mood').textContent = elder.mood || 'Neutral';
    $('dossier-mood').style.color = moodColor(elder.mood);
    $('dossier-belief-bar').style.width = (elder.belief_in_divine ?? 50) + '%';

    // Cached? Show instantly, skip the billed call.
    const cached = state.dossierCache[elder.name];
    const fill = (data) => {
        $('dossier-biography').textContent = data.biography || 'The archives contain no records of this elder’s life.';
        const rel = $('dossier-relationships');
        rel.innerHTML = '';
        const rels = data.relationships || [];
        if (rels.length) rels.forEach((r) => { const li = document.createElement('li'); li.textContent = r; rel.appendChild(li); });
        else { const li = document.createElement('li'); li.textContent = 'No known grudges or alliances.'; rel.appendChild(li); }
    };

    if (cached) { $('dossier-loading').classList.add('hidden'); $('dossier-body').classList.remove('hidden'); fill(cached); return; }

    $('dossier-body').classList.add('hidden');
    $('dossier-loading').classList.remove('hidden');
    try {
        const data = await api(`/api/elder_dossier/${KINGDOM_ID}/${encodeURIComponent(elder.name)}`);
        state.dossierCache[elder.name] = data;
        fill(data);
    } catch (e) {
        $('dossier-biography').textContent = 'Error consulting the Royal Archives. The backend is unresponsive.';
        $('dossier-relationships').innerHTML = '<li>Network Error</li>';
    }
    $('dossier-loading').classList.add('hidden');
    $('dossier-body').classList.remove('hidden');
}

async function handleOracleSubmit() {
    const query = $('oracle-input').value.trim();
    if (!query) return;
    const log = $('oracle-chat-log');

    const pm = document.createElement('div');
    pm.className = 'oracle-msg player'; pm.textContent = query;
    log.appendChild(pm);
    $('oracle-input').value = '';

    const loading = document.createElement('div');
    loading.className = 'oracle-msg loading'; loading.textContent = 'The Tapestry shifts and hums...';
    log.appendChild(loading);
    log.scrollTop = log.scrollHeight;

    try {
        const data = await postJSON('/api/oracle', { query });
        loading.remove();
        const om = document.createElement('div');
        om.className = 'oracle-msg oracle'; om.textContent = data.answer || 'The Tapestry is silent.';
        log.appendChild(om);
    } catch (e) {
        loading.remove();
        const em = document.createElement('div');
        em.className = 'oracle-msg oracle'; em.textContent = 'The connection to the Archives has been severed. Start the backend server.';
        log.appendChild(em);
    }
    log.scrollTop = log.scrollHeight;
}

function showAdaptationJourney(a) {
    const name = a.display_name || a;
    const effect = a.gameplay_effect || '';
    const triggers = (a.trigger_events || []).join(' → ');
    $('detail-title').textContent = `${name}`;
    $('detail-desc').textContent = effect
        ? `${effect}${triggers ? '  Born of: ' + triggers : ''}`
        : 'Ask the Oracle to recall how this adaptation came to be.';
    $('adaptation-detail-box').classList.remove('hidden');
}

async function openTapestry() {
    const container = $('tapestry-tree-container');
    container.innerHTML = '<div class="tapestry-empty">Unrolling the Tapestry...</div>';
    $('tapestry-modal').classList.remove('hidden');
    try {
        const data = await api('/causality_timeline');
        const tree = data.timeline || [];
        container.innerHTML = '';
        if (!tree.length) { container.innerHTML = '<div class="tapestry-empty">The Tapestry is bare. History has not yet been woven.</div>'; return; }
        const ul = renderTapestryTree(tree);
        if (ul) container.appendChild(ul);
    } catch (e) {
        container.innerHTML = '<div class="tapestry-empty">The Tapestry is lost to the mists. (Is the backend running?)</div>';
    }
}

function renderTapestryTree(nodes) {
    if (!nodes || nodes.length === 0) return null;
    const ul = document.createElement('ul');
    nodes.forEach((node) => {
        const li = document.createElement('li');
        const nodeDiv = document.createElement('div');
        nodeDiv.className = 'tree-node';
        nodeDiv.innerHTML = `
            <div class="tree-year">Year ${node.year}, ${node.season}</div>
            <div class="tree-title">${node.title}</div>
            <div class="tree-intervention"><span>Decree / Consequence</span>${node.intervention || 'None recorded'}</div>`;
        nodeDiv.addEventListener('click', () => {
            $('lore-title').textContent = node.title;
            $('lore-meta').textContent = `Year ${node.year}, ${node.season}`;
            $('lore-narrative').textContent = node.narrative || 'The chronicles are damaged. This history is lost to time.';
            $('lore-decree').textContent = node.intervention || 'None recorded';
            $('lore-modal').classList.remove('hidden');
        });
        li.appendChild(nodeDiv);
        const childrenUl = renderTapestryTree(node.children);
        if (childrenUl) li.appendChild(childrenUl);
        ul.appendChild(li);
    });
    return ul;
}

// ============================================================
//  WIRING
// ============================================================
function setupEventListeners() {
    $('close-detail-btn').addEventListener('click', () => $('adaptation-detail-box').classList.add('hidden'));
    $('tapestry-btn').addEventListener('click', openTapestry);
    $('close-tapestry-btn').addEventListener('click', () => $('tapestry-modal').classList.add('hidden'));
    $('close-lore-btn').addEventListener('click', () => $('lore-modal').classList.add('hidden'));
    $('close-dossier-btn').addEventListener('click', () => $('dossier-modal').classList.add('hidden'));

    $('oracle-btn').addEventListener('click', () => { $('oracle-modal').classList.remove('hidden'); $('oracle-input').focus(); });
    $('close-oracle-btn').addEventListener('click', () => $('oracle-modal').classList.add('hidden'));
    $('oracle-send-btn').addEventListener('click', handleOracleSubmit);
    $('oracle-input').addEventListener('keypress', (e) => { if (e.key === 'Enter') handleOracleSubmit(); });

    $('council-skip-btn').addEventListener('click', skipCouncil);
    $('decree-stamp-btn').addEventListener('click', resolveCouncil);
    $('endgame-restart-btn').addEventListener('click', restartGame);
    $('proceed-btn').addEventListener('click', proceed);

    // Click narrative to skip typewriter
    $('situation-narrative').addEventListener('click', () => {
        if (typewriterTimer && state.situation) {
            clearInterval(typewriterTimer);
            const el = $('situation-narrative');
            el.textContent = state.situation.narrative || '';
            el.classList.remove('typewriter-caret'); el.classList.add('dropcap');
        }
    });

    // Consequence badge → trace the chain in the Tapestry of Fate
    $('consequence-badge').addEventListener('click', openTapestry);
}

async function init() {
    setupEventListeners();

    try {
        const world = await loadWorld();

        if (world.kingdom.game_status && world.kingdom.game_status !== 'active') {
            return showEndgame(world.kingdom.game_status);
        }
        // Unrest already at the boiling point → resume/convene the council (reuse if present: no re-bill)
        if (world.kingdom.realm_unrest >= COUNCIL_UNREST_THRESHOLD) {
            if (world.active_council) return runCouncil(world.active_council);
            return runCouncil();
        }
        // Re-render a persisted turn (situation + minor cards + locks) instead of re-billing
        const stored = localStorage.getItem(SIT_KEY);
        if (stored) {
            try {
                const t = JSON.parse(stored);
                const sit = t.sit || t;                 // tolerate the old situation-only shape
                state.minorCards = t.minorCards || [];
                state.locked = t.locked || { situation: null, minors: {} };
                if (!state.locked.minors) state.locked.minors = {};
                renderSituation(sit);
                return;
            } catch (e) { /* fall through to a fresh generation */ }
        }
        await generateSituation();
    } catch (e) {
        showError('Could not reach the Realm.', e);
    }
}

// ============================================================
//  TITLE SCREEN
// ============================================================
let newGameArmed = null; // holds the disarm timeout id while "New Game" is armed for confirmation

async function initTitleScreen() {
    if (window.Atmosphere) window.Atmosphere.init(); // background runs behind the title too

    const newBtn = $('title-new-btn');
    const loadBtn = $('title-load-btn');

    // Cheap read-only probe (no LLM cost) to tell an untouched kingdom from a real save.
    let hasSave = false;
    try {
        const world = await api('/world_state');
        const k = world.kingdom;
        hasSave = (world.chronicle && world.chronicle.length > 0) ||
                  (world.adaptations && world.adaptations.length > 0) ||
                  k.current_year > 1 || k.food !== 50 || k.realm_unrest !== 20;
    } catch (e) { /* backend unreachable — leave Load Game disabled */ }

    loadBtn.disabled = !hasSave;

    newBtn.addEventListener('click', async () => {
        if (hasSave && newGameArmed === null) {
            newBtn.textContent = 'Erase kingdom & begin anew?';
            newBtn.classList.add('confirm-armed');
            newGameArmed = setTimeout(() => {
                newBtn.textContent = 'New Game';
                newBtn.classList.remove('confirm-armed');
                newGameArmed = null;
            }, 4000);
            return;
        }
        if (newGameArmed !== null) { clearTimeout(newGameArmed); newGameArmed = null; }
        await startNewGame();
    });

    loadBtn.addEventListener('click', () => {
        $('title-screen').classList.add('hidden');
        init();
    });

    $('title-credits-btn').addEventListener('click', () => $('credits-modal').classList.remove('hidden'));
    $('close-credits-btn').addEventListener('click', () => $('credits-modal').classList.add('hidden'));
}

async function startNewGame() {
    $('title-screen').classList.add('hidden');
    showLoading('A new age dawns...');
    try {
        await postJSON('/reset');
        localStorage.removeItem(SIT_KEY);
        state.dossierCache = {};
        await init();
    } catch (e) {
        showError('The world would not begin anew.', e);
    } finally {
        hideLoading(); // safety net — init()'s own branches manage this too, but never leave the veil stuck
    }
}

document.addEventListener('DOMContentLoaded', initTitleScreen);
