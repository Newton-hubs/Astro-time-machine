/**
 * ============================================================
 * ASTRO TIME MACHINE — script.js
 * Vanilla JS frontend for the FastAPI Astro Time Machine API
 * 
 * API Endpoints used:
 *   POST /api/v1/astronomy/sky           → Sky snapshot
 *   POST /api/v1/astronomy/location/resolve → City → coords
 *   POST /api/v1/narration/generate      → AI narration text
 *
 * Architecture:
 *   - State object holds all app state
 *   - Pure functions for UI updates
 *   - Modular sections: Stars, Location, API, Display
 * ============================================================
 */

/* ── Config ─────────────────────────────────────────────── */
const CONFIG = {
  API_BASE: 'http://localhost:8000',           // FastAPI server URL
  STAR_COUNT: 160,                             // Number of background stars
  LOADING_MESSAGES: [
    'Computing celestial positions…',
    'Calculating moon phase…',
    'Locating visible planets…',
    'Rendering sky map…',
    'Fetching cloud data…',
  ],
};

/* ── Application State ──────────────────────────────────── */
const state = {
  locationMode: 'manual',      // 'manual' | 'city' | 'gps'
  latitude: 12.9716,
  longitude: 77.5946,
  locationName: '',
  lastSnapshotId: null,         // Used for narration request
  isLoading: false,
};

/* ========================================================
   SECTION 1: STARRY BACKGROUND
   ======================================================== */

/**
 * Injects random star elements into the star field container.
 * Each star gets random position, size, brightness, and twinkling timing.
 */
function buildStarField() {
  const container = document.getElementById('starField');
  const fragment = document.createDocumentFragment();

  for (let i = 0; i < CONFIG.STAR_COUNT; i++) {
    const star = document.createElement('div');
    star.className = 'star';

    // Random position
    const x = Math.random() * 100;
    const y = Math.random() * 100;

    // Vary size: most tiny, a few larger
    const rand = Math.random();
    const size = rand > 0.97 ? 3 : rand > 0.88 ? 2 : 1;

    // Random twinkling params via CSS custom properties
    const duration  = (2.5 + Math.random() * 4).toFixed(1);
    const delay     = (Math.random() * 6).toFixed(1);
    const minAlpha  = (0.1 + Math.random() * 0.2).toFixed(2);
    const maxAlpha  = (0.6 + Math.random() * 0.4).toFixed(2);

    star.style.cssText = `
      left: ${x}%;
      top: ${y}%;
      width: ${size}px;
      height: ${size}px;
      --twinkle-dur: ${duration}s;
      --twinkle-delay: ${delay}s;
      --star-min: ${minAlpha};
      --star-max: ${maxAlpha};
      opacity: ${minAlpha};
    `;

    fragment.appendChild(star);
  }

  container.appendChild(fragment);
}

/* ========================================================
   SECTION 2: LOCATION HANDLING
   ======================================================== */

/**
 * Switches between Manual, City Search, and GPS modes.
 * Updates UI toggles and shows the relevant location block.
 * @param {string} mode - 'manual' | 'city' | 'gps'
 */
function setLocationMode(mode) {
  state.locationMode = mode;

  // Update button states
  ['manual', 'city', 'gps'].forEach(m => {
    const btn = document.getElementById(`btn${capitalize(m)}`);
    if (!btn) return;
    
    btn.classList.toggle('active', m === mode);
    btn.setAttribute('aria-pressed', m === mode ? 'true' : 'false');
  });

  // Hide all location blocks
  ['blockManual', 'blockCity', 'blockGPS'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });

  // Show only the selected mode's block
  const blockId = {
    manual: 'blockManual',
    city: 'blockCity',
    gps: 'blockGPS'
  }[mode];

  if (blockId) {
    document.getElementById(blockId).classList.remove('hidden');
  }

  // Hide the resolved location badge when switching modes
  hideElement('resolvedLocation');
}

/**
 * Calls the backend /location/resolve endpoint to convert
 * a city name into lat/lon coordinates.
 */
async function resolveCity() {
  const cityInput = document.getElementById('inputCity').value.trim();
  const status    = document.getElementById('cityStatus');

  if (!cityInput) {
    status.textContent = 'Please enter a city name.';
    return;
  }

  status.textContent = 'Searching…';
  const btn = document.getElementById('btnSearchCity');
  btn.disabled = true;

  try {
    const result = await apiPost('/api/v1/astronomy/location/resolve', {
      location_name: cityInput,
    });

    // Store resolved coordinates in state
    state.latitude     = result.latitude;
    state.longitude    = result.longitude;
    state.locationName = result.location_name;

    // Populate coordinate inputs for transparency
    document.getElementById('inputLat').value = result.latitude.toFixed(4);
    document.getElementById('inputLon').value = result.longitude.toFixed(4);
    document.getElementById('inputLocName').value = result.location_name;

    // Show resolved badge
    document.getElementById('resolvedName').textContent =
      `${result.location_name}${result.country ? ', ' + result.country : ''}`;
    showElement('resolvedLocation');

    status.textContent = '';
  } catch (err) {
    status.textContent = `⚠ ${err.message || 'City not found.'}`;
  } finally {
    btn.disabled = false;
  }
}

/**
 * Uses the browser Geolocation API to get the user's current position.
 * Falls back gracefully if permission is denied.
 */
function detectGPS() {
  const status = document.getElementById('gpsStatus');

  if (!navigator.geolocation) {
    status.textContent = '⚠ Geolocation not supported by this browser.';
    return;
  }

  status.textContent = 'Requesting GPS signal…';

  navigator.geolocation.getCurrentPosition(
    (position) => {
      // Success: store coordinates
      state.latitude  = position.coords.latitude;
      state.longitude = position.coords.longitude;

      document.getElementById('inputLat').value = state.latitude.toFixed(4);
      document.getElementById('inputLon').value = state.longitude.toFixed(4);

      document.getElementById('resolvedName').textContent =
        `${state.latitude.toFixed(4)}°, ${state.longitude.toFixed(4)}°`;
      showElement('resolvedLocation');

      status.textContent = `✔ Location acquired.`;
    },
    (error) => {
      // Permission denied or error
      const messages = {
        1: 'Permission denied — please allow location access.',
        2: 'Position unavailable — try manual input.',
        3: 'Request timed out — try again.',
      };
      status.textContent = `⚠ ${messages[error.code] || 'Unknown error.'}`;
    },
    { timeout: 10000, maximumAge: 60000 }
  );
}

/* ========================================================
   SECTION 3: API CALLS
   ======================================================== */

/**
 * Generic POST helper with error handling.
 * @param {string} path - API endpoint path (e.g. '/api/v1/astronomy/sky')
 * @param {object} body - Request payload
 * @returns {Promise<object>} - Parsed JSON response
 */
async function apiPost(path, body) {
  const response = await fetch(`${CONFIG.API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    // Try to extract error detail from FastAPI response
    let detail = `HTTP ${response.status}`;
    try {
      const errData = await response.json();
      detail = errData.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  return response.json();
}

/**
 * Main function — triggered by "Generate Sky" button.
 * Orchestrates: validate → call sky API → display results → call narration API.
 */
async function generateSky() {
  if (state.isLoading) return;

  hideError();

  // ── 1. Read and validate form inputs ──
  const dateVal   = document.getElementById('inputDate').value;
  const timeVal   = document.getElementById('inputTime').value;
  const locName   = document.getElementById('inputLocName').value.trim();

  // Always read lat/lon from the visible inputs (they may have been updated by GPS/city)
  const latInput = parseFloat(document.getElementById('inputLat').value);
  const lonInput = parseFloat(document.getElementById('inputLon').value);

  if (!dateVal || !timeVal) {
    showError('Please provide both a date and time.');
    return;
  }

  if (isNaN(latInput) || latInput < -90 || latInput > 90) {
    showError('Latitude must be between -90 and 90.');
    return;
  }

  if (isNaN(lonInput) || lonInput < -180 || lonInput > 180) {
    showError('Longitude must be between -180 and 180.');
    return;
  }

  // Build UTC ISO datetime string from local date + time inputs
  // Note: The API expects UTC; we're treating user input as local and converting
  const datetimeLocal = `${dateVal}T${timeVal}:00`;
  const datetimeUTC   = new Date(datetimeLocal).toISOString();

  const payload = {
    latitude:      latInput,
    longitude:     lonInput,
    datetime_utc:  datetimeUTC,
    location_name: locName || state.locationName || undefined,
  };

  // ── 2. Enter loading state ──
  setLoading(true);

  try {
    // ── 3. Call sky snapshot endpoint ──
    const skyData = await apiPost('/api/v1/astronomy/sky', payload);

    // Store snapshot ID for narration
    state.lastSnapshotId = skyData.snapshot_id;

    // ── 4. Display sky visualization + data ──
    displaySkyResults(skyData);

    // ── 5. Request AI narration (non-blocking, shows after) ──
    requestNarration(skyData.snapshot_id);

  } catch (err) {
    showError(err.message || 'Failed to reach the API. Is the server running?');
    resetSkyDisplay();
  } finally {
    setLoading(false);
  }
}

/**
 * Fires a narration request after the sky data is shown.
 * Shows a separate section when it resolves.
 * @param {string} snapshotId - ID from the sky endpoint
 */
async function requestNarration(snapshotId) {
  try {
    const narration = await apiPost('/api/v1/narration/generate', {
      sky_snapshot_id: snapshotId,
      voice: false,
    });

    displayNarration(narration);
  } catch (_) {
    // Narration is a bonus — silently fail if unavailable
  }
}

/* ========================================================
   SECTION 4: DISPLAY / RENDER FUNCTIONS
   ======================================================== */

/**
 * Renders the full sky result: image, info tiles, and metadata.
 * @param {object} data - SkySnapshotResponse from the API
 */
function displaySkyResults(data) {
  // ── Sky image ──
  if (data.visualization?.image_base64) {
    const img = document.getElementById('skyImage');
    img.src = `data:image/png;base64,${data.visualization.image_base64}`;
    img.classList.remove('hidden');
    document.getElementById('skyPlaceholder').classList.add('hidden');
  }

  // ── Metadata pill ──
  const dt = new Date(data.datetime_utc);
  document.getElementById('metaDatetime').textContent =
    dt.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  document.getElementById('metaCoords').textContent =
    `${data.latitude.toFixed(3)}°, ${data.longitude.toFixed(3)}°`;
  showElement('snapshotMeta');

  // ── Moon tile ──
  const moon = data.moon;
  setTileValue('valMoonPhase', moon.phase_name);
  setTileValue('valMoonIllum', `${moon.illumination_pct.toFixed(1)}% illuminated`);
  markTilePopulated('tileMoon');

  // ── Visibility tile ──
  let visText = moon.is_above_horizon ? 'Above horizon' : 'Below horizon';
  if (moon.is_above_horizon && moon.is_cloud_obscured) visText = 'Cloud obscured';
  setTileValue('valVisibility', visText);
  setTileValue(
    'valAltAz',
    `Alt ${moon.altitude_deg.toFixed(1)}°  Az ${moon.azimuth_deg.toFixed(1)}°`
  );
  markTilePopulated('tileVis');

  // ── Planets tile ──
  const visiblePlanets = data.planets.filter(p => p.is_visible);
  const planetsList    = document.getElementById('valPlanets');

  if (visiblePlanets.length === 0) {
    planetsList.textContent = 'None visible';
  } else {
    planetsList.innerHTML = '';
    visiblePlanets.forEach(planet => {
      const tag = document.createElement('span');
      tag.className = 'planet-tag';
      tag.textContent = planet.name;
      if (planet.magnitude !== null) {
        tag.title = `Magnitude: ${planet.magnitude.toFixed(1)}`;
      }
      planetsList.appendChild(tag);
    });
  }
  markTilePopulated('tilePlanets');

  // ── Weather tile ──
  if (data.weather) {
    setTileValue('valCloud', `${data.weather.cloud_cover_pct.toFixed(0)}%`);
    setTileValue('valCloudDesc', data.weather.description);
  } else {
    setTileValue('valCloud', 'N/A');
    setTileValue('valCloudDesc', 'No weather data');
  }
  markTilePopulated('tileWeather');
}

/**
 * Shows the AI narration section with text and optional model badge.
 * @param {object} narration - NarrationResponse from the API
 */
function displayNarration(narration) {
  document.getElementById('narrationText').textContent = narration.narration_text;
  document.getElementById('modelBadge').textContent    = narration.model_used || '';
  showElement('narrationSection');

  // Smooth scroll to narration
  document.getElementById('narrationSection').scrollIntoView({
    behavior: 'smooth',
    block: 'nearest',
  });
}

/**
 * Resets the sky display to its initial placeholder state.
 */
function resetSkyDisplay() {
  document.getElementById('skyImage').classList.add('hidden');
  document.getElementById('skyPlaceholder').classList.remove('hidden');
  hideElement('snapshotMeta');
}

/* ========================================================
   SECTION 5: UI STATE HELPERS
   ======================================================== */

/**
 * Enters or exits the loading state.
 * Shows spinner, disables button, cycles loading messages.
 * @param {boolean} loading
 */
function setLoading(loading) {
  state.isLoading = loading;

  const btn      = document.getElementById('btnGenerate');
  const spinner  = document.getElementById('skyLoading');
  const loadTxt  = document.getElementById('loadingText');

  btn.disabled = loading;

  if (loading) {
    // Show spinner over sky viewport
    spinner.classList.remove('hidden');
    hideElement('skyImage');
    hideElement('skyPlaceholder');
    hideElement('narrationSection');

    // Cycle through loading messages for engagement
    let msgIdx = 0;
    loadTxt.textContent = CONFIG.LOADING_MESSAGES[0];
    state._loadingInterval = setInterval(() => {
      msgIdx = (msgIdx + 1) % CONFIG.LOADING_MESSAGES.length;
      loadTxt.textContent = CONFIG.LOADING_MESSAGES[msgIdx];
    }, 1800);
  } else {
    spinner.classList.add('hidden');
    clearInterval(state._loadingInterval);
  }
}

/** Shows an error message in the error box */
function showError(message) {
  document.getElementById('errorText').textContent = message;
  document.getElementById('errorBox').classList.remove('hidden');
}

/** Hides the error box */
function hideError() {
  document.getElementById('errorBox').classList.add('hidden');
  document.getElementById('errorText').textContent = '';
}

/** Sets the text content of a tile value element */
function setTileValue(id, text) {
  document.getElementById(id).textContent = text;
}

/** Adds the 'populated' class to a tile to trigger the entrance animation */
function markTilePopulated(tileId) {
  const tile = document.getElementById(tileId);
  // Remove and re-add the class to retrigger animation on subsequent queries
  tile.classList.remove('populated');
  // Force reflow so the animation retriggers
  void tile.offsetWidth;
  tile.classList.add('populated');
}

/** Shows a hidden element by removing the 'hidden' class */
function showElement(id) {
  document.getElementById(id).classList.remove('hidden');
}

/** Hides an element by adding the 'hidden' class */
function hideElement(id) {
  document.getElementById(id).classList.add('hidden');
}

/** Capitalizes first letter of a string */
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/* ========================================================
   SECTION 6: INITIALIZATION
   ======================================================== */

/**
 * Sets up the page on first load:
 * - Builds star field
 * - Sets default date/time to today / 21:00
 * - Initializes location mode
 */
function init() {
  // Build starry background
  buildStarField();

  // Set default date to today
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('inputDate').value = today;

  // Input listeners: keep state in sync when user types lat/lon manually
  document.getElementById('inputLat').addEventListener('change', e => {
    state.latitude = parseFloat(e.target.value) || 0;
  });
  document.getElementById('inputLon').addEventListener('change', e => {
    state.longitude = parseFloat(e.target.value) || 0;
  });

  // Allow pressing Enter in city search input
  document.getElementById('inputCity').addEventListener('keydown', e => {
    if (e.key === 'Enter') resolveCity();
  });

  // Initialize location mode (manual by default)
  setLocationMode('manual');

  console.log('[AstroTimeMachine] Ready. API Base:', CONFIG.API_BASE);
}

// Run init once the DOM is fully loaded
document.addEventListener('DOMContentLoaded', init);
