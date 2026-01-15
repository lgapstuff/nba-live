// API Configuration
const API_BASE_URL = 'http://localhost:8000';
const CDN_API_BASE_URL = `${API_BASE_URL}/nba/cdn`;
const CDN_SCOREBOARD_TTL_MS = 30000;
const LIVE_BOXSCORE_REFRESH_MS = 45000;
const cachedCdnBoxscores = new Map();
let cachedCdnScoreboard = null;
let cachedCdnScoreboardAt = 0;
let liveBoxscoreIntervalId = null;

// DOM Elements
const scheduleUploadSection = document.getElementById('schedule-upload-section');
const scheduleFileInput = document.getElementById('schedule-file-input');
// Depth chart file input removed - now loaded automatically from NBA API
const loadSchedulesBtn = document.getElementById('load-schedules-btn');
const lineupsActionsSection = document.getElementById('lineups-actions-section');
const loadLineupsBtn = document.getElementById('load-lineups-btn');
const loadScoresBtn = document.getElementById('load-scores-btn');
const loadingDiv = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const errorDiv = document.getElementById('error');
const gamesContainer = document.getElementById('games-container');
const lineupsView = document.getElementById('lineups-view');
const valuePlayersView = document.getElementById('value-players-view');
const valuePlayersContainer = document.getElementById('value-players-container');
const lineupsActions = document.getElementById('lineups-actions');

// Store loaded games data to avoid unnecessary HTTP calls
let cachedGamesData = null;

// Get today's date in Los Angeles/Tijuana timezone (America/Los_Angeles)
function getTodayInLATimezone() {
    // Get current time in Los Angeles timezone
    const now = new Date();
    const laTime = new Date(now.toLocaleString("en-US", {timeZone: "America/Los_Angeles"}));
    
    // Format as YYYY-MM-DD
    const year = laTime.getFullYear();
    const month = String(laTime.getMonth() + 1).padStart(2, '0');
    const day = String(laTime.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

// Format time in Los Angeles timezone
function formatTimeInLATimezone(dateString) {
    if (!dateString) return 'N/A';
    let liveApplied = false;
    try {
        const date = new Date(dateString);
        
        // Use Intl.DateTimeFormat for proper timezone conversion
        const formatter = new Intl.DateTimeFormat("en-US", {
            timeZone: "America/Los_Angeles",
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
        
        // Use formatToParts to get individual parts and ensure correct formatting
        const parts = formatter.formatToParts(date);
        const hour = parts.find(part => part.type === 'hour')?.value || '00';
        const minute = parts.find(part => part.type === 'minute')?.value || '00';
        
        return `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
    } catch (e) {
        console.error('Error formatting time in LA timezone:', dateString, e);
        return 'N/A';
    }
}

function normalizeTeamTricode(team) {
    const normalized = (team || '').toString().trim().toUpperCase();
    const map = {
        'NO': 'NOP',
        'NY': 'NYK',
        'GS': 'GSW',
        'PHO': 'PHX',
        'SA': 'SAS'
    };
    return map[normalized] || normalized;
}

function parseIsoDurationToSeconds(duration) {
    if (!duration || typeof duration !== 'string') return null;
    const match = duration.match(/PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?/);
    if (!match) return null;
    const minutes = match[1] ? parseInt(match[1], 10) : 0;
    const seconds = match[2] ? Math.floor(parseFloat(match[2])) : 0;
    return (minutes * 60) + seconds;
}

function formatSecondsToClock(seconds) {
    if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
        return '-';
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

async function fetchCdnScoreboard() {
    const now = Date.now();
    if (cachedCdnScoreboard && (now - cachedCdnScoreboardAt) < CDN_SCOREBOARD_TTL_MS) {
        return cachedCdnScoreboard;
    }
    const response = await fetch(`${CDN_API_BASE_URL}/scoreboard/today`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json'
        }
    });
    if (!response.ok) {
        throw new Error(`CDN scoreboard error: ${response.status}`);
    }
    const data = await response.json();
    if (!data.success || !data.scoreboard) {
        throw new Error(data.error || 'CDN scoreboard no data');
    }
    cachedCdnScoreboard = data.scoreboard;
    cachedCdnScoreboardAt = now;
    return cachedCdnScoreboard;
}

function findCdnGameForTeams(scoreboard, awayTeam, homeTeam) {
    if (!scoreboard || !scoreboard.scoreboard || !scoreboard.scoreboard.games) {
        return null;
    }
    const away = normalizeTeamTricode(awayTeam);
    const home = normalizeTeamTricode(homeTeam);
    return scoreboard.scoreboard.games.find(game => {
        const cdnAway = normalizeTeamTricode(game?.awayTeam?.teamTricode);
        const cdnHome = normalizeTeamTricode(game?.homeTeam?.teamTricode);
        return cdnAway === away && cdnHome === home;
    }) || null;
}

async function fetchCdnBoxscore(gameId, forceRefresh = false) {
    if (!forceRefresh && cachedCdnBoxscores.has(gameId)) {
        return cachedCdnBoxscores.get(gameId);
    }
    const cacheBust = forceRefresh ? `?t=${Date.now()}` : '';
    const response = await fetch(`${CDN_API_BASE_URL}/boxscore/${gameId}${cacheBust}`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json'
        }
    });
    if (!response.ok) {
        throw new Error(`CDN boxscore error: ${response.status}`);
    }
    const data = await response.json();
    if (!data.success || !data.boxscore) {
        throw new Error(data.error || 'CDN boxscore no data');
    }
    cachedCdnBoxscores.set(gameId, data.boxscore);
    return data.boxscore;
}

function getGameElapsedInfo(cdnGame) {
    if (!cdnGame) return null;
    const period = cdnGame.period || 0;
    const regulationPeriods = cdnGame.regulationPeriods || 4;
    const isOvertime = period > regulationPeriods;
    const periodLengthSeconds = isOvertime ? 5 * 60 : 12 * 60;
    const remainingSeconds = parseIsoDurationToSeconds(cdnGame.gameClock);
    if (remainingSeconds === null || period === 0) {
        return null;
    }
    const completedRegPeriods = Math.min(period - 1, regulationPeriods);
    const completedOtPeriods = Math.max(0, period - regulationPeriods - 1);
    const elapsedSeconds = (completedRegPeriods * 12 * 60) +
        (completedOtPeriods * 5 * 60) +
        (periodLengthSeconds - remainingSeconds);
    const totalSeconds = (regulationPeriods * 12 * 60) + (Math.max(0, period - regulationPeriods) * 5 * 60);
    return {
        statusText: cdnGame.gameStatusText || '',
        elapsedSeconds,
        totalSeconds
    };
}

function getLiveCenterStatus(cdnGame) {
    if (!cdnGame) return { text: '', isTimeout: false };
    const statusText = String(cdnGame.gameStatusText || '').trim();
    const lowerStatus = statusText.toLowerCase();
    const isTimeout = lowerStatus.includes('timeout') || lowerStatus.includes('time out') || lowerStatus.includes('tiempo fuera');
    if (isTimeout) {
        return { text: statusText || 'TIMEOUT', isTimeout: true };
    }
    const period = cdnGame.period || 0;
    const remainingSeconds = parseIsoDurationToSeconds(cdnGame.gameClock);
    if (remainingSeconds !== null && period > 0) {
        return { text: `Q${period} ${formatSecondsToClock(remainingSeconds)}`, isTimeout: false };
    }
    if (statusText) {
        return { text: statusText, isTimeout: false };
    }
    return { text: '', isTimeout: false };
}

function isCdnGameFinished(cdnGame) {
    if (!cdnGame) return false;
    const statusText = String(cdnGame.gameStatusText || '').toLowerCase();
    if (statusText.includes('final') || statusText.includes('finished') || statusText.includes('terminado')) {
        return true;
    }
    const statusCode = Number(cdnGame.gameStatus);
    return statusCode === 3;
}

function removeFinishedGameCard(gameId, card) {
    if (card && card.parentNode) {
        card.parentNode.removeChild(card);
    }
    if (cachedGamesData && Array.isArray(cachedGamesData)) {
        cachedGamesData = cachedGamesData.filter(game => String(game.game_id) !== String(gameId));
    }
}

async function updateLiveInfoForGames(games) {
    if (!games || games.length === 0) return;
    try {
        const scoreboard = await fetchCdnScoreboard();
        games.forEach(game => {
            const cdnGame = findCdnGameForTeams(scoreboard, game.away_team, game.home_team);
            if (!cdnGame) return;
            game.nba_game_id = cdnGame.gameId;
            const card = document.querySelector(`.game-card[data-game-id="${game.game_id}"]`);
            if (!card) return;
            if (isCdnGameFinished(cdnGame)) {
                removeFinishedGameCard(game.game_id, card);
                return;
            }
            card.setAttribute('data-nba-game-id', cdnGame.gameId || '');
            const liveInfo = card.querySelector('.game-live-info');
            if (!liveInfo) return;
            const centerStatusEl = card.querySelector('.game-center-status');
            if (centerStatusEl) {
                const centerStatus = getLiveCenterStatus(cdnGame);
                centerStatusEl.textContent = centerStatus.text;
                centerStatusEl.classList.toggle('active', Boolean(centerStatus.text));
                centerStatusEl.classList.toggle('timeout', centerStatus.isTimeout);
            }
            const elapsedInfo = getGameElapsedInfo(cdnGame);
            const centerText = centerStatusEl ? centerStatusEl.textContent.trim() : '';
            if (!elapsedInfo) {
                liveInfo.textContent = centerText ? '' : (cdnGame.gameStatusText || '');
                return;
            }
            liveInfo.innerHTML = `
                <span class="live-status-text">${centerText ? '' : elapsedInfo.statusText}</span>
            `;
            liveInfo.classList.add('active');
        });
    } catch (error) {
        console.warn('No se pudo cargar info live de CDN:', error);
    }
}

async function getCdnGameForInternalGame(gameId) {
    const game = cachedGamesData?.find(g => String(g.game_id) === String(gameId));
    if (!game) return null;
    const scoreboard = await fetchCdnScoreboard();
    return findCdnGameForTeams(scoreboard, game.away_team, game.home_team);
}

function extractCdnPlayerStats(boxscore, playerId) {
    if (!boxscore || !boxscore.game) return null;
    const teams = [boxscore.game.homeTeam, boxscore.game.awayTeam];
    for (const team of teams) {
        const players = team?.players || [];
        const player = players.find(p => String(p.personId) === String(playerId));
        if (player) {
            const stats = player.statistics || {};
            return {
                playerName: player.name || '',
                points: stats.points ?? 0,
                assists: stats.assists ?? 0,
                rebounds: stats.reboundsTotal ?? 0,
                foulsPersonal: stats.foulsPersonal ?? stats.fouls ?? 0,
                minutes: stats.minutes || 'PT00M00S',
                onCourt: String(player.oncourt) === '1',
                starter: String(player.starter) === '1'
            };
        }
    }
    return null;
}

function formatIsoMinutes(duration) {
    const seconds = parseIsoDurationToSeconds(duration);
    return seconds === null ? '-' : formatSecondsToClock(seconds);
}

function getSuggestedDirection(player, statType) {
    if (!player || !player.over_under_history) return '';
    const history = player.over_under_history;
    let over = 0;
    let under = 0;
    if (statType === 'points') {
        over = history.over_count || 0;
        under = history.under_count || 0;
    } else if (statType === 'assists') {
        over = history.assists_over_count || 0;
        under = history.assists_under_count || 0;
    } else if (statType === 'rebounds') {
        over = history.rebounds_over_count || 0;
        under = history.rebounds_under_count || 0;
    }
    const total = over + under;
    if (!total || over === under) return '';
    return over > under ? 'over' : 'under';
}

function renderSuggestionArrow(direction) {
    if (direction === 'over') {
        return '<span class="stat-arrow up" title="Sugerencia: OVER">↑</span>';
    }
    if (direction === 'under') {
        return '<span class="stat-arrow down" title="Sugerencia: UNDER">↓</span>';
    }
    return '';
}

function getSuggestedDirection(player, statType) {
    if (!player || !player.over_under_history) return '';
    const history = player.over_under_history;
    let over = 0;
    let under = 0;
    if (statType === 'points') {
        over = history.over_count || 0;
        under = history.under_count || 0;
    } else if (statType === 'assists') {
        over = history.assists_over_count || 0;
        under = history.assists_under_count || 0;
    } else if (statType === 'rebounds') {
        over = history.rebounds_over_count || 0;
        under = history.rebounds_under_count || 0;
    }
    const total = over + under;
    if (!total) return '';
    if (over === under) return '';
    return over > under ? 'over' : 'under';
}

function renderSuggestionArrow(direction) {
    if (direction === 'over') {
        return '<span class="stat-arrow up" title="Sugerencia: OVER">↑</span>';
    }
    if (direction === 'under') {
        return '<span class="stat-arrow down" title="Sugerencia: UNDER">↓</span>';
    }
    return '';
}

async function fetchLivePlayerSummary(playerId, gameId) {
    if (!gameId || !playerId) return null;
    try {
        const cdnGame = await getCdnGameForInternalGame(gameId);
        if (!cdnGame || !cdnGame.gameId) return null;
        const boxscore = await fetchCdnBoxscore(cdnGame.gameId);
        const stats = extractCdnPlayerStats(boxscore, playerId);
        if (!stats) return null;
        const elapsedInfo = getGameElapsedInfo(cdnGame);
        return { stats, cdnGame, elapsedInfo };
    } catch (error) {
        console.warn('No se pudo cargar live summary:', error);
        return null;
    }
}

function renderLivePlayerSummary(modalBody, summary) {
    if (!modalBody) return;
    const existing = modalBody.querySelector('.live-player-summary');
    if (existing) existing.remove();
    if (!summary) return;
    const { stats, elapsedInfo, cdnGame } = summary;
    const onCourtLabel = stats.onCourt ? 'EN CANCHA' : 'EN BANCA';
    const statusText = elapsedInfo?.statusText || cdnGame?.gameStatusText || 'LIVE';
    const timeText = elapsedInfo
        ? `Tiempo: ${formatSecondsToClock(elapsedInfo.elapsedSeconds)} / ${formatSecondsToClock(elapsedInfo.totalSeconds)}`
        : '';
    const fouls = summary.stats.foulsPersonal ?? summary.stats.fouls ?? 0;
    const html = `
        <div class="live-player-summary ${stats.onCourt ? 'on-court' : ''}">
            <div class="live-player-summary-header">
                <span class="live-tag">LIVE</span>
                <span class="live-status-text">${statusText}</span>
                ${timeText ? `<span class="live-time-text">${timeText}</span>` : ''}
            </div>
            <div class="live-player-summary-stats">
                <span class="live-stat">${stats.points} PTS</span>
                <span class="live-stat">${stats.assists} AST</span>
                <span class="live-stat">${stats.rebounds} REB</span>
                <span class="live-stat">${fouls} PF</span>
                <span class="live-stat">${formatIsoMinutes(stats.minutes)} MIN</span>
                <span class="live-stat">${onCourtLabel}</span>
            </div>
        </div>
    `;
    modalBody.insertAdjacentHTML('afterbegin', html);
}

function normalizePlayerName(name) {
    if (!name) return '';
    return name
        .toString()
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function buildCdnPlayersIndex(boxscore) {
    const index = {};
    if (!boxscore || !boxscore.game) return index;
    const teams = [boxscore.game.homeTeam, boxscore.game.awayTeam];
    teams.forEach(team => {
        const tricode = normalizeTeamTricode(team?.teamTricode);
        if (!tricode) return;
        const players = team?.players || [];
        const byId = new Map();
        const byName = new Map();
        players.forEach(player => {
            if (player?.personId) {
                byId.set(String(player.personId), player);
            }
            const normalized = normalizePlayerName(player?.name);
            if (normalized) {
                byName.set(normalized, player);
            }
        });
        index[tricode] = { byId, byName };
    });
    return index;
}

function resolveCdnPlayer(index, teamTricode, playerId, playerName) {
    const teamIndex = index[normalizeTeamTricode(teamTricode)] || null;
    const normalizedName = normalizePlayerName(playerName);
    if (teamIndex && normalizedName && teamIndex.byName.has(normalizedName)) {
        return teamIndex.byName.get(normalizedName);
    }
    const idKey = playerId ? String(playerId) : null;
    if (teamIndex && idKey && teamIndex.byId.has(idKey)) {
        return teamIndex.byId.get(idKey);
    }
    // Fallback: try all teams by name
    if (normalizedName) {
        for (const key of Object.keys(index)) {
            const teamData = index[key];
            if (teamData.byName.has(normalizedName)) {
                return teamData.byName.get(normalizedName);
            }
        }
    }
    return null;
}

function formatLiveStatsText(stats, onCourt) {
    const fouls = stats.foulsPersonal ?? stats.fouls ?? 0;
    const minutes = formatIsoMinutes(stats.minutes);
    const onCourtLabel = onCourt ? 'EN CANCHA' : 'EN BANCA';
    return `
        <span class="live-tag">LIVE</span>
        <span class="live-stat">${stats.points ?? 0} PTS</span>
        <span class="live-stat">${stats.assists ?? 0} AST</span>
        <span class="live-stat">${stats.reboundsTotal ?? 0} REB</span>
        <span class="live-stat">${fouls} PF</span>
        <span class="live-stat">${minutes} MIN</span>
        <span class="live-stat">${onCourtLabel}</span>
    `;
}

async function applyLiveBoxscoreToGame(gameId, forceRefresh = false) {
    const game = cachedGamesData?.find(g => String(g.game_id) === String(gameId));
    const gameCard = document.querySelector(`.game-card[data-game-id="${gameId}"]`);
    if (!gameCard || !game) return;

    let nbaGameId = game.nba_game_id || gameCard.getAttribute('data-nba-game-id');
    if (!nbaGameId) {
        const scoreboard = await fetchCdnScoreboard();
        const cdnGame = findCdnGameForTeams(scoreboard, game.away_team, game.home_team);
        nbaGameId = cdnGame?.gameId || '';
        if (cdnGame?.gameId) {
            game.nba_game_id = cdnGame.gameId;
            gameCard.setAttribute('data-nba-game-id', cdnGame.gameId);
        }
    }

    if (!nbaGameId) {
        throw new Error('No se encontró el NBA GameID en CDN para este juego');
    }

    const boxscore = await fetchCdnBoxscore(nbaGameId, forceRefresh);
    const index = buildCdnPlayersIndex(boxscore);

    const playerCards = gameCard.querySelectorAll('.position-card');
    playerCards.forEach(card => {
        const playerId = card.getAttribute('data-player-id');
        const playerName = card.getAttribute('data-player-name');
        const teamLineup = card.closest('.team-lineup');
        const teamAbbr = teamLineup?.getAttribute('data-team-abbr') || '';
        const cdnPlayer = resolveCdnPlayer(index, teamAbbr, playerId, playerName);
        const liveStatsEl = card.querySelector('.player-live-stats');
        if (!liveStatsEl) return;
        if (!cdnPlayer || !cdnPlayer.statistics) {
            liveStatsEl.textContent = 'Live: sin datos';
            liveStatsEl.classList.remove('active', 'on-court');
            return;
        }
        const onCourt = String(cdnPlayer.oncourt) === '1';
        liveStatsEl.innerHTML = formatLiveStatsText(cdnPlayer.statistics, onCourt);
        liveStatsEl.classList.add('active');
        liveStatsEl.classList.toggle('on-court', onCourt);
    });
}

function startLiveBoxscorePolling() {
    if (liveBoxscoreIntervalId) {
        clearInterval(liveBoxscoreIntervalId);
    }
    liveBoxscoreIntervalId = setInterval(async () => {
        if (!cachedGamesData || cachedGamesData.length === 0) return;
        try {
            const scoreboard = await fetchCdnScoreboard();
            cachedGamesData.forEach(game => {
                const cdnGame = findCdnGameForTeams(scoreboard, game.away_team, game.home_team);
                if (!cdnGame) return;
                const card = document.querySelector(`.game-card[data-game-id="${game.game_id}"]`);
                if (!card) return;
                if (isCdnGameFinished(cdnGame)) {
                    removeFinishedGameCard(game.game_id, card);
                    return;
                }
                const statusText = String(cdnGame.gameStatusText || '').toLowerCase();
                const statusCode = Number(cdnGame.gameStatus);
                const isLive = statusCode === 2 ||
                    statusText.includes('live') ||
                    statusText.includes('q') ||
                    statusText.includes('half') ||
                    statusText.includes('ot');
                if (!isLive) return;
                applyLiveBoxscoreToGame(game.game_id, true).catch(error => {
                    console.warn('No se pudo refrescar boxscore live:', error);
                });
            });
        } catch (error) {
            console.warn('No se pudo refrescar scoreboard live:', error);
        }
    }, LIVE_BOXSCORE_REFRESH_MS);
}

// Event Listeners
loadSchedulesBtn.addEventListener('click', () => {
    // Open file picker for schedule file
    scheduleFileInput.click();
});
scheduleFileInput.addEventListener('change', handleScheduleFileSelect);
loadLineupsBtn.addEventListener('click', loadLineups);
if (loadScoresBtn) {
    loadScoresBtn.addEventListener('click', loadScoresForAllGames);
    loadScoresBtn.classList.add('hidden');
}

// Check if schedule exists for today and load accordingly
async function checkScheduleAndLoad() {
    const today = getTodayInLATimezone();
    
    try {
        const response = await fetch(`${API_BASE_URL}/nba/games?date=${today}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.games && data.games.length > 0) {
            // Schedule exists, show games and lineups actions
            scheduleUploadSection.classList.add('hidden');
            lineupsActionsSection.classList.remove('hidden');
            // Load lineups if they exist
            await loadGamesWithLineups(today);
        } else {
            // No schedule for today, show button
            scheduleUploadSection.classList.remove('hidden');
            lineupsActionsSection.classList.add('hidden');
            gamesContainer.innerHTML = '';
        }
    } catch (error) {
        console.error('Error checking schedule:', error);
        // On error, show the button so user can try to load
        scheduleUploadSection.classList.remove('hidden');
        lineupsActionsSection.classList.add('hidden');
    }
}

// Handle schedule file selection (rosters loaded automatically from NBA API)
async function handleScheduleFileSelect(event) {
    const scheduleFile = scheduleFileInput.files[0];
    
    if (!scheduleFile) {
        showError('Por favor selecciona el archivo de schedule');
        return;
    }
    
    // Show loading
    loadingText.textContent = 'Cargando schedule y rosters desde NBA API...';
    showLoading();
    hideError();
    gamesContainer.innerHTML = '';
    
    try {
        const formData = new FormData();
        formData.append('schedule_file', scheduleFile);
        
        const response = await fetch(`${API_BASE_URL}/nba/schedule/import`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Schedule and rosters loaded successfully, now load games for today
            showSuccess(`Schedule cargado: ${data.schedule?.saved_games || 0} juegos. Rosters: ${data.rosters?.teams_processed || 0} equipos.`);
            await loadGames();
            // Hide the upload section and show lineups actions
            scheduleUploadSection.classList.add('hidden');
            lineupsActionsSection.classList.remove('hidden');
          } else {
            throw new Error(data.message || 'Error al cargar schedule y rosters');
          }
        
    } catch (error) {
        console.error('Error loading schedule and rosters:', error);
        showError(`Error al cargar schedule y rosters: ${error.message || error}`);
    } finally {
        hideLoading();
        // Reset file input
        scheduleFileInput.value = '';
    }
}

// Load lineups function (imports lineups from FantasyNerds)
async function loadLineups() {
    const today = getTodayInLATimezone();
    
    // Show loading
    loadingText.textContent = `Cargando lineups desde FantasyNerds para hoy (${today})...`;
    showLoading();
    hideError();
    
    try {
        const response = await fetch(`${API_BASE_URL}/nba/lineups/import?date=${today}`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Reload games with lineups
            await loadGamesWithLineups(today);
        } else {
            throw new Error(data.message || 'Error al cargar lineups');
        }
        
    } catch (error) {
        console.error('Error loading lineups:', error);
        showError(`Error al cargar lineups: ${error.message || error}`);
    } finally {
        hideLoading();
    }
}

// Load game logs for an event (must be in global scope)
window.loadGameLogsForGame = async function(gameId, buttonElement) {
    console.log('loadGameLogsForGame called with gameId:', gameId);
    
    if (!gameId) {
        console.error('No gameId provided');
        showError('Error: No se proporcionó un ID de juego');
        return;
    }
    
    if (!buttonElement) {
        console.error('No buttonElement provided');
        showError('Error: No se proporcionó el elemento del botón');
        return;
    }
    
    // Find the game card
    const gameCard = buttonElement
        ? buttonElement.closest('.game-card')
        : document.querySelector(`.game-card[data-game-id="${gameId}"]`);
    if (!gameCard) {
        showError('Error: No se pudo encontrar la carta del juego');
        return;
    }
    
    // Get only selected players (with checkbox checked)
    const allCheckboxes = gameCard.querySelectorAll('.player-game-log-checkbox');
    const checkedCheckboxes = gameCard.querySelectorAll('.player-game-log-checkbox:checked');
    
    console.log(`[loadGameLogsForGame] Total checkboxes: ${allCheckboxes.length}, Checked: ${checkedCheckboxes.length}`);
    
    const selectedPlayers = [];
    
    checkedCheckboxes.forEach(checkbox => {
        const playerId = checkbox.getAttribute('data-player-id');
        const playerName = checkbox.getAttribute('data-player-name') || '';
        const playerCard = checkbox.closest('[data-player-id]');
        
        console.log(`[loadGameLogsForGame] Processing checkbox - playerId: ${playerId}, playerName: ${playerName}, card found: ${!!playerCard}`);
        
        if (playerId && playerId !== '' && playerCard) {
            selectedPlayers.push({
                id: parseInt(playerId),
                name: playerName,
                card: playerCard,
                checkbox: checkbox
            });
        }
    });
    
    console.log(`[loadGameLogsForGame] Selected players: ${selectedPlayers.length}`);
    
    if (selectedPlayers.length === 0) {
        showError('Por favor selecciona al menos un jugador para cargar game logs');
        return;
    }
    
    // Show loading state on button
    const btnText = buttonElement.querySelector('.btn-text') || buttonElement;
    const countSpan = btnText.querySelector('.selected-count') || gameCard.querySelector('.selected-count');
    const originalButtonText = 'Cargar Game Logs';
    
    // Update button to show loading state
    const updateButtonText = (count) => {
        if (count > 0) {
            // Show loading state - replace entire btn-text content
            btnText.innerHTML = `Cargando ${count}...`;
        } else {
            // Restore original text with count span
            if (countSpan) {
                countSpan.textContent = '0';
                btnText.innerHTML = `${originalButtonText} (<span class="selected-count">0</span>)`;
            } else {
                btnText.innerHTML = `${originalButtonText} (<span class="selected-count">0</span>)`;
            }
        }
    };
    
    buttonElement.disabled = true;
    updateButtonText(selectedPlayers.length);
    
    // Track which players to uncheck at the end
    const playersToUncheck = [];
    
    try {
        console.log(`Loading game logs for ${selectedPlayers.length} selected players in game ${gameId}`);
        
        let successCount = 0;
        let skippedCount = 0;
        let errorCount = 0;
        let totalGamesLoaded = 0;
        let remainingCount = selectedPlayers.length;
        
        // Process selected players one by one
        for (let i = 0; i < selectedPlayers.length; i++) {
            const player = selectedPlayers[i];
            console.log(`Loading game logs for player ${player.id} (${player.name}) - ${i + 1}/${selectedPlayers.length}`);
            
            // First check if player already has game logs
            try {
                const checkUrl = `${API_BASE_URL}/nba/players/${player.id}/game-logs?player_name=${encodeURIComponent(player.name)}`;
                const checkResponse = await fetch(checkUrl, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                });
                
                if (checkResponse.ok) {
                    const checkData = await checkResponse.json();
                    if (checkData.success && checkData.total_games && checkData.total_games >= 10) {
                        // Player already has enough game logs, skip
                        console.log(`✓ Player ${player.name} already has ${checkData.total_games} game logs, skipping...`);
                        skippedCount++;
                        playersToUncheck.push(player);
                        remainingCount--;
                        updateButtonText(remainingCount);
                        continue;
                    }
                }
            } catch (checkError) {
                console.warn(`Could not check existing game logs for ${player.name}:`, checkError);
                // Continue to load anyway
            }
            
            // Show loading indicator on player card
            showPlayerCardLoading(player.card, player.name);
            
            try {
                const url = `${API_BASE_URL}/nba/players/${player.id}/game-logs/load?player_name=${encodeURIComponent(player.name)}&num_games=25`;
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        successCount++;
                        totalGamesLoaded += data.games_loaded || 0;
                        console.log(`✓ Loaded ${data.games_loaded || 0} games for ${player.name}`);
                        // Mark for unchecking at the end
                        playersToUncheck.push(player);
                    } else {
                        errorCount++;
                        console.warn(`✗ Failed to load games for ${player.name}: ${data.message || 'Unknown error'}`);
                    }
                } else {
                    errorCount++;
                    const errorText = await response.text();
                    console.warn(`✗ HTTP ${response.status} for ${player.name}: ${errorText}`);
                }
            } catch (error) {
                errorCount++;
                console.error(`✗ Error loading game logs for ${player.name}:`, error);
            } finally {
                // Hide loading indicator on player card
                hidePlayerCardLoading(player.card);
                remainingCount--;
                updateButtonText(remainingCount);
            }
        }
        
        // Uncheck all processed players at once to avoid layout shifts
        playersToUncheck.forEach(player => {
            if (player.checkbox) {
                player.checkbox.checked = false;
            }
        });
        
        // Update the count one final time (after unchecking)
        // Use setTimeout to ensure DOM updates are complete
        setTimeout(() => {
            updateSelectedCount(gameCard);
        }, 0);
        
        // Show summary
        let message = '';
        if (successCount > 0) {
            message = `Game logs cargados: ${successCount} jugadores, ${totalGamesLoaded} juegos`;
            if (skippedCount > 0) {
                message += ` (${skippedCount} ya tenían game logs)`;
            }
            if (errorCount > 0) {
                message += ` (${errorCount} errores)`;
            }
            showSuccess(message);
        } else if (skippedCount > 0) {
            showSuccess(`Todos los jugadores seleccionados ya tienen game logs cargados`);
        } else {
            showError(`No se pudieron cargar game logs para ningún jugador`);
        }
        
    } catch (error) {
        console.error('Error loading game logs for game:', error);
        showError(`Error al cargar game logs: ${error.message || error}`);
    } finally {
        // First, uncheck all processed players (if not already done)
        playersToUncheck.forEach(player => {
            if (player.checkbox && player.checkbox.checked) {
                player.checkbox.checked = false;
            }
        });
        
        // Get final count after unchecking
        const finalCount = gameCard.querySelectorAll('.player-game-log-checkbox:checked').length;
        
        // Restore button text with proper HTML structure
        btnText.innerHTML = `${originalButtonText} (<span class="selected-count">${finalCount}</span>)`;
        
        // Update button state
        if (finalCount === 0) {
            buttonElement.disabled = true;
            buttonElement.style.opacity = '0.5';
            buttonElement.style.cursor = 'not-allowed';
        } else {
            buttonElement.disabled = false;
            buttonElement.style.opacity = '1';
            buttonElement.style.cursor = 'pointer';
        }
        
        // Live Player Score button removed
        
        // Update count using the function (which will find the newly created span)
        // Use a small delay to ensure DOM is updated
        setTimeout(() => {
            updateSelectedCount(gameCard);
        }, 10);
    }
};

// Toggle select all players for a game
window.toggleSelectAllPlayers = function(gameId, buttonElement) {
    const gameCard = buttonElement
        ? buttonElement.closest('.game-card')
        : document.querySelector(`.game-card[data-game-id="${gameId}"]`);
    if (!gameCard) return;
    
    const checkboxes = gameCard.querySelectorAll('.player-game-log-checkbox');
    const checkedCount = gameCard.querySelectorAll('.player-game-log-checkbox:checked').length;
    const allChecked = checkedCount === checkboxes.length;
    
    // Toggle all checkboxes
    checkboxes.forEach(checkbox => {
        checkbox.checked = !allChecked;
    });
    
    // Update button text
    const btnText = buttonElement.querySelector('.btn-text') || buttonElement;
    btnText.textContent = allChecked ? 'Seleccionar Todos' : 'Deseleccionar Todos';
    
    // Update selected count
    updateSelectedCount(gameCard);
};

// Update selected count display
function updateSelectedCount(gameCard) {
    if (!gameCard) return;
    
    const checkboxes = gameCard.querySelectorAll('.player-game-log-checkbox');
    const checkedCount = gameCard.querySelectorAll('.player-game-log-checkbox:checked').length;
    
    console.log(`[updateSelectedCount] Found ${checkboxes.length} checkboxes, ${checkedCount} checked`);
    
    // Try to find the count span - first in the button, then in the game card
    const loadButton = gameCard.querySelector('.load-game-logs-btn');
    let countSpan = null;
    
    if (loadButton) {
        // Look for selected-count inside the button's btn-text
        const btnText = loadButton.querySelector('.btn-text');
        if (btnText) {
            countSpan = btnText.querySelector('.selected-count');
        }
        // If not found, try direct query
        if (!countSpan) {
            countSpan = loadButton.querySelector('.selected-count');
        }
    }
    
    // If still not found, search in the entire game card
    if (!countSpan) {
        countSpan = gameCard.querySelector('.selected-count');
    }
    
    if (countSpan) {
        countSpan.textContent = checkedCount;
        console.log(`[updateSelectedCount] Updated count to ${checkedCount}`);
    } else {
        console.warn('[updateSelectedCount] Could not find .selected-count element');
        // Try to recreate it if button exists
        if (loadButton) {
            const btnText = loadButton.querySelector('.btn-text') || loadButton;
            if (btnText && !btnText.querySelector('.selected-count')) {
                // Restore the button structure if it's missing
                const originalText = 'Cargar Game Logs';
                btnText.innerHTML = `${originalText} (<span class="selected-count">${checkedCount}</span>)`;
                console.log(`[updateSelectedCount] Recreated button structure with count ${checkedCount}`);
            }
        }
    }
    
    // Enable/disable load button based on selection
    if (loadButton) {
        loadButton.disabled = checkedCount === 0;
        if (checkedCount === 0) {
            loadButton.style.opacity = '0.5';
            loadButton.style.cursor = 'not-allowed';
        } else {
            loadButton.style.opacity = '1';
            loadButton.style.cursor = 'pointer';
            loadButton.removeAttribute('disabled');
        }
        console.log(`[updateSelectedCount] Button disabled: ${loadButton.disabled}, checkedCount: ${checkedCount}`);
    } else {
        console.warn('[updateSelectedCount] Could not find .load-game-logs-btn element');
    }
    
    // Live Player Score button removed
}

// Show loading indicator on a player card
function showPlayerCardLoading(playerCard, playerName) {
    if (!playerCard) return;
    
    // Add loading class
    playerCard.classList.add('loading');
    
    // Create or update loading overlay
    let overlay = playerCard.querySelector('.player-loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'player-loading-overlay';
        // Ensure parent has position relative (should already be set in CSS)
        if (window.getComputedStyle(playerCard).position === 'static') {
            playerCard.style.position = 'relative';
        }
        playerCard.appendChild(overlay);
    }
    overlay.innerHTML = `
        <div class="player-loading-spinner"></div>
        <div class="player-loading-text">Cargando...</div>
    `;
    overlay.classList.add('active');
}

// Hide loading indicator on a player card
function hidePlayerCardLoading(playerCard) {
    if (!playerCard) return;
    
    // Remove loading class
    playerCard.classList.remove('loading');
    
    // Hide loading overlay
    const overlay = playerCard.querySelector('.player-loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        // Remove overlay after animation
        setTimeout(() => {
            if (overlay && overlay.parentNode) {
                overlay.remove();
            }
        }, 300);
    }
}

// Load roster for a specific game (must be in global scope for onclick)
window.loadRosterForGame = async function(gameId, buttonElement) {
    console.log('loadRosterForGame called with gameId:', gameId);
    
    if (!gameId) {
        console.error('No gameId provided');
        showError('Error: No se proporcionó un ID de juego');
        return;
    }
    
    if (!buttonElement) {
        console.error('No buttonElement provided');
        showError('Error: No se proporcionó el elemento del botón');
        return;
    }
    
    // Find the game card for this specific game
    const gameCard = buttonElement
        ? buttonElement.closest('.game-card')
        : document.querySelector(`.game-card[data-game-id="${gameId}"]`);
    if (!gameCard) {
        showError('Error: No se pudo encontrar la carta del juego');
        return;
    }
    
    // Show loading state on button
    const btnText = buttonElement.querySelector('.btn-text') || buttonElement;
    const originalText = btnText.textContent;
    btnText.textContent = 'Cargando...';
    buttonElement.disabled = true;
    
    try {
        console.log(`Loading rosters for game ${gameId} from ${API_BASE_URL}/nba/games/${gameId}/rosters`);
        
        const response = await fetch(`${API_BASE_URL}/nba/games/${gameId}/rosters`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Roster data received:', data);
        
        if (data.success) {
            const teamsProcessed = data.teams_processed || 0;
            const teamsSkipped = data.teams_skipped || 0;
            const playersSaved = data.players_saved || 0;
            
            let message = `Rosters cargados: ${teamsProcessed} equipos, ${playersSaved} jugadores guardados.`;
            if (teamsSkipped > 0) {
                message += ` ${teamsSkipped} equipos ya tenían roster y se omitieron.`;
            }
            showSuccess(message);
            
            // Hide the button since rosters are now loaded
            buttonElement.style.display = 'none';
        } else {
            throw new Error(data.message || 'Error al cargar rosters');
        }
        
    } catch (error) {
        console.error('Error loading rosters for game:', error);
        showError(`Error al cargar rosters: ${error.message || error}`);
    } finally {
        // Restore button state
        btnText.textContent = originalText;
        buttonElement.disabled = false;
    }
};

// Load live player stats for selected players (must be in global scope for onclick)
// Live Player Score button removed

// Load scores for a specific game (must be in global scope for onclick)
window.loadScoresForGame = async function(gameId, buttonElement) {
    console.log('loadScoresForGame called with gameId:', gameId);
    
    if (!gameId) {
        showError('Error: No se proporcionó un ID de juego');
        return;
    }
    
    const gameCard = buttonElement
        ? buttonElement.closest('.game-card')
        : document.querySelector(`.game-card[data-game-id="${gameId}"]`);
    if (!gameCard) {
        showError('Error: No se pudo encontrar la carta del juego');
        return;
    }
    
    // Show loading overlay on the specific game card
    showGameCardLoading(gameCard);
    
    // Show loading state on button
    const originalText = buttonElement ? buttonElement.textContent : '';
    if (buttonElement) {
        buttonElement.textContent = 'Cargando...';
        buttonElement.disabled = true;
    }
    let liveApplied = false;
    
    try {
        console.log(`Fetching scores for game ${gameId} from ${API_BASE_URL}/nba/games/${gameId}/scores`);
        
        const response = await fetch(`${API_BASE_URL}/nba/games/${gameId}/scores`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Scores data received:', data);
        
        if (data.success) {
            console.log('Scores loaded successfully, updating game card...');
            
            // Get updated game data - try lineups endpoint first, then games endpoint
            let gameData = null;
            const lineupResponse = await fetch(`${API_BASE_URL}/nba/games/${gameId}/lineups`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (lineupResponse.ok) {
                const lineupData = await lineupResponse.json();
                if (lineupData.success && lineupData.lineup) {
                    gameData = lineupData.lineup;
                }
            }
            
            // If no lineup data, try games endpoint
            if (!gameData) {
                const today = getTodayInLATimezone();
                const gamesResponse = await fetch(`${API_BASE_URL}/nba/games?date=${today}`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                });
                
                if (gamesResponse.ok) {
                    const gamesData = await gamesResponse.json();
                    if (gamesData.success && gamesData.games) {
                        gameData = gamesData.games.find(g => g.game_id === gameId);
                    }
                }
            }
            
            if (gameData) {
                // Recreate the game card with updated scores
                const hasLineups = gameData.lineups && Object.keys(gameData.lineups).length > 0;
                const newCard = createGameCard(gameData, hasLineups);
                gameCard.replaceWith(newCard);
                updateLiveInfoForGames([gameData]);
                try {
                    await applyLiveBoxscoreToGame(gameId);
                    liveApplied = true;
                } catch (error) {
                    console.warn('No se pudo aplicar boxscore live:', error);
                }
                
                // Re-attach event listeners
                const loadOddsButton = newCard.querySelector('.load-odds-btn');
                if (loadOddsButton) {
                    loadOddsButton.addEventListener('click', function() {
                        const gameId = this.getAttribute('data-game-id');
                        loadOddsForGame(gameId, this);
                    });
                }
                
                const loadScoresButton = newCard.querySelector('.load-scores-btn');
                if (loadScoresButton) {
                    loadScoresButton.addEventListener('click', function() {
                        const gameId = this.getAttribute('data-game-id');
                        loadScoresForGame(gameId, this);
                    });
                }
                
                // Re-attach checkbox listeners and update selected count
                if (hasLineups) {
                    const checkboxes = newCard.querySelectorAll('.player-game-log-checkbox');
                    checkboxes.forEach(checkbox => {
                        checkbox.addEventListener('change', function() {
                            updateSelectedCount(newCard);
                        });
                        checkbox.addEventListener('click', function() {
                            setTimeout(() => {
                                updateSelectedCount(newCard);
                            }, 10);
                        });
                    });
                    updateSelectedCount(newCard);
                }
                
                // Update cached games data
                if (cachedGamesData) {
                    const gameIndex = cachedGamesData.findIndex(g => g.game_id === gameId);
                    if (gameIndex !== -1) {
                        cachedGamesData[gameIndex] = gameData;
                    }
                }
                
                // Re-attach other listeners if needed
                if (hasLineups) {
                    const selectAllButtons = newCard.querySelectorAll('.select-all-players-btn');
                    selectAllButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const gameId = this.getAttribute('data-game-id');
                            toggleSelectAllPlayers(gameId, this);
                        });
                    });
                    
                    // Re-attach team toggle buttons
                    const teamToggleButtons = newCard.querySelectorAll('.team-toggle-btn');
                    teamToggleButtons.forEach(button => {
                        // Event listener is already attached via onclick in HTML
                    });
                    
                    const loadGameLogsButtons = newCard.querySelectorAll('.load-game-logs-btn');
                    loadGameLogsButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const gameId = this.getAttribute('data-game-id');
                            loadGameLogsForGame(gameId, this);
                        });
                    });
                    
                    // Live Player Score button removed
                } else {
                    const loadRosterButtons = newCard.querySelectorAll('.load-roster-btn');
                    loadRosterButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const gameId = this.getAttribute('data-game-id');
                            loadRosterForGame(gameId, this);
                        });
                    });
                }
            }
            
            if (buttonElement) {
                showSuccess('Scores cargados exitosamente');
            }
        } else {
            throw new Error(data.message || 'Error al cargar scores');
        }
        
    } catch (error) {
        console.error('Error loading scores for game:', error);
        showError(`Error al cargar scores: ${error.message || error}`);
    } finally {
        // Hide loading overlay
        hideGameCardLoading(gameCard);
        // Restore button state
        if (buttonElement) {
            buttonElement.textContent = originalText;
            buttonElement.disabled = false;
        }
        if (!liveApplied) {
            try {
                await applyLiveBoxscoreToGame(gameId);
            } catch (error) {
                console.warn('No se pudo aplicar boxscore live:', error);
            }
        }
    }
};

function loadScoresForAllGames() {
    if (!cachedGamesData || cachedGamesData.length === 0) {
        showError('No hay juegos cargados todavía.');
        return;
    }
    const originalText = loadScoresBtn ? loadScoresBtn.textContent : '';
    if (loadScoresBtn) {
        loadScoresBtn.textContent = 'Cargando...';
        loadScoresBtn.disabled = true;
    }
    Promise.all(
        cachedGamesData.map(game => loadScoresForGame(game.game_id, null))
    ).then(() => {
        showSuccess('Scores cargados para todos los juegos');
    }).catch((error) => {
        console.error('Error loading scores for all games:', error);
        showError(`Error al cargar scores: ${error.message || error}`);
    }).finally(() => {
        if (loadScoresBtn) {
            loadScoresBtn.textContent = originalText;
            loadScoresBtn.disabled = false;
        }
    });
}

// Load odds for a specific game (must be in global scope for onclick)
window.loadOddsForGame = async function(gameId, buttonElement) {
    console.log('loadOddsForGame called with gameId:', gameId);
    
    if (!gameId) {
        console.error('No gameId provided');
        showError('Error: No se proporcionó un ID de juego');
        return;
    }
    
    // First check if depth charts exist
    try {
        const checkResponse = await fetch(`${API_BASE_URL}/nba/depth-charts/check`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (checkResponse.ok) {
            const checkData = await checkResponse.json();
            if (!checkData.has_depth_charts) {
                showError('Debes cargar Depth Charts antes de cargar Odds. Por favor carga los Depth Charts primero.');
                return;
            }
        }
    } catch (error) {
        console.warn('Could not check depth charts:', error);
        // Continue anyway, backend will validate
    }
    
    // Find the game card for this specific game
    const gameCard = buttonElement
        ? buttonElement.closest('.game-card')
        : document.querySelector(`.game-card[data-game-id="${gameId}"]`);
    if (!gameCard) {
        showError('Error: No se pudo encontrar la carta del juego');
        return;
    }
    
    // Show loading overlay on the specific game card
    showGameCardLoading(gameCard);
    
    // Show loading state on button
    const btnText = buttonElement ? (buttonElement.querySelector('.btn-text') || buttonElement) : null;
    const originalText = btnText ? btnText.textContent : '';
    if (btnText) {
        btnText.textContent = 'Cargando...';
    }
    if (buttonElement) {
        buttonElement.disabled = true;
    }
    
    try {
        console.log(`Fetching odds for game ${gameId} from ${API_BASE_URL}/nba/games/${gameId}/odds`);
        
        const response = await fetch(`${API_BASE_URL}/nba/games/${gameId}/odds`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Odds data received:', data);
        
        if (data.success) {
            console.log('Odds loaded successfully, updating game card...');
            // Update only this specific game card instead of reloading all games
            const gameData = await updateGameCardWithLineups(gameId, gameCard);
            await loadScoresForGame(gameId, null);
            
            // Expand game card after loading odds
            expandGameCard(gameCard);
            
            // Update cached games data with the updated game
            if (cachedGamesData && gameData) {
                const gameIndex = cachedGamesData.findIndex(g => g.game_id === gameId);
                if (gameIndex !== -1) {
                    cachedGamesData[gameIndex] = gameData;
                }
            }
            
            // If value players view is active, refresh it to show updated players (using cached data, no HTTP call)
            if (valuePlayersView && valuePlayersView.classList.contains('active')) {
                await loadValuePlayers();
            }
        } else {
            throw new Error(data.message || 'Error al cargar odds');
        }
        
    } catch (error) {
        console.error('Error loading odds for game:', error);
        showError(`Error al cargar odds: ${error.message || error}`);
    } finally {
        // Hide loading overlay
        hideGameCardLoading(gameCard);
        // Restore button state
        if (btnText) {
            btnText.textContent = originalText;
        }
        if (buttonElement) {
            buttonElement.disabled = false;
        }
    }
};

// Update a specific game card with lineups (without reloading all games)
async function updateGameCardWithLineups(gameId, gameCard) {
    try {
        // Get lineups for this specific game
        const response = await fetch(`${API_BASE_URL}/nba/games/${gameId}/lineups`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.warn(`Could not fetch lineups for game ${gameId}, keeping existing card`);
            return;
        }
        
        const data = await response.json();
        
        // The endpoint returns {success: true, game_id: ..., lineup: {...}}
        // The lineup object contains the game data with lineups
        if (data.success && data.lineup) {
            // The lineup object has the structure: {game_id, game_date, lineups: {...}, ...}
            const gameData = {
                ...data.lineup,
                game_id: gameId
            };
            if (cachedGamesData) {
                const idx = cachedGamesData.findIndex(g => String(g.game_id) === String(gameId));
                if (idx >= 0) {
                    cachedGamesData[idx] = gameData;
                } else {
                    cachedGamesData.push(gameData);
                }
            } else {
                cachedGamesData = [gameData];
            }
            
            // Replace the game card content with updated data
            const newCard = createGameCard(gameData, true);
            // Preserve the game card's position in the container
            gameCard.replaceWith(newCard);
            updateLiveInfoForGames([gameData]);
            try {
                await applyLiveBoxscoreToGame(gameId);
            } catch (error) {
                console.warn('No se pudo aplicar boxscore live:', error);
            }
            
            // Re-attach event listeners to the new card
            const loadOddsButton = newCard.querySelector('.load-odds-btn');
            if (loadOddsButton) {
                loadOddsButton.addEventListener('click', function() {
                    const gameId = this.getAttribute('data-game-id');
                    loadOddsForGame(gameId, this);
                });
            }
            
            // Scores are loaded automatically when odds load
            
            // Re-attach checkbox listeners and update selected count
            const checkboxes = newCard.querySelectorAll('.player-game-log-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    updateSelectedCount(newCard);
                });
                checkbox.addEventListener('click', function() {
                    setTimeout(() => {
                        updateSelectedCount(newCard);
                    }, 10);
                });
            });
            
            // Live Player Score button removed
            
            updateSelectedCount(newCard);
            
            // Return the gameData so it can be used by the caller
            return gameData;
        }
        
        return null;
    } catch (error) {
        console.error(`Error updating game card ${gameId}:`, error);
        // Don't show error to user, just log it - the card will remain as is
        return null;
    }
}

// Load games with lineups
async function loadGamesWithLineups(date = null) {
    const today = date || getTodayInLATimezone();
    
    // Show loading
    loadingText.textContent = 'Cargando juegos con lineups...';
    showLoading();
    hideError();
    gamesContainer.innerHTML = '';
    
    try {
        const url = `${API_BASE_URL}/nba/lineups?date=${today}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.games && data.games.length > 0) {
            cachedGamesData = data.games;
            displayGames(data.games, true); // true = has lineups
        } else {
            // No lineups, but show games from schedule
            await loadGames();
        }
        
    } catch (error) {
        console.error('Error loading games with lineups:', error);
        showError(`Error al cargar juegos: ${error.message || error}`);
    } finally {
        hideLoading();
    }
}

// Load games function (gets games from schedule)
async function loadGames() {
    const today = getTodayInLATimezone();
    
    // Show loading
    loadingText.textContent = 'Cargando juegos...';
    showLoading();
    hideError();
    gamesContainer.innerHTML = '';
    
    try {
        const url = `${API_BASE_URL}/nba/games?date=${today}`;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const errorText = await response.text();
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.games && data.games.length > 0) {
            // Cache games data (even without lineups)
            cachedGamesData = data.games;
            displayGames(data.games);
        } else {
            showEmptyState('No hay juegos disponibles para hoy');
        }
        
    } catch (error) {
        console.error('Error details:', error);
        let errorMessage = 'Error desconocido';
        
        if (error.name === 'AbortError') {
            errorMessage = 'La petición tardó demasiado. Intenta de nuevo.';
        } else if (error.message) {
            errorMessage = error.message;
        } else if (error.toString) {
            errorMessage = error.toString();
        }

        showError(`Error al cargar juegos: ${errorMessage}`);
    } finally {
        hideLoading();
    }
}

// Display games
function displayGames(games, hasLineups = false) {
    gamesContainer.innerHTML = '';
    
    games.forEach(game => {
        const gameCard = createGameCard(game, hasLineups);
        gamesContainer.appendChild(gameCard);
    });
    
    // Add event listeners to all action buttons
    if (hasLineups) {
        // Select all buttons
        const selectAllButtons = gamesContainer.querySelectorAll('.select-all-players-btn');
        selectAllButtons.forEach(button => {
            button.addEventListener('click', function() {
                const gameId = this.getAttribute('data-game-id');
                toggleSelectAllPlayers(gameId, this);
            });
        });
        
        // Game logs buttons
        const loadGameLogsButtons = gamesContainer.querySelectorAll('.load-game-logs-btn');
        loadGameLogsButtons.forEach(button => {
            button.addEventListener('click', function() {
                const gameId = this.getAttribute('data-game-id');
                loadGameLogsForGame(gameId, this);
            });
        });
        
        // Initialize selected count for each game card and add checkbox listeners
        gamesContainer.querySelectorAll('.game-card').forEach(gameCard => {
            // Initialize immediately
            updateSelectedCount(gameCard);
            
            // Add checkbox change listeners for this game card
            const checkboxes = gameCard.querySelectorAll('.player-game-log-checkbox');
            console.log(`[displayGames] Found ${checkboxes.length} checkboxes in game card`);
            checkboxes.forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    console.log(`[checkbox change] Checkbox changed, updating count`);
                    updateSelectedCount(gameCard);
                });
            });
            
            // Also listen for clicks on the checkboxes (in case change event doesn't fire)
            checkboxes.forEach(checkbox => {
                checkbox.addEventListener('click', function() {
                    setTimeout(() => {
                        console.log(`[checkbox click] Checkbox clicked, updating count`);
                        updateSelectedCount(gameCard);
                    }, 10);
                });
            });
        });
        
        // Odds buttons
        const loadOddsButtons = gamesContainer.querySelectorAll('.load-odds-btn');
        loadOddsButtons.forEach(button => {
            button.addEventListener('click', function() {
                const gameId = this.getAttribute('data-game-id');
                loadOddsForGame(gameId, this);
            });
        });
        
        // Scores buttons
        // Scores are loaded automatically when odds load
        
        // Live Player Score button removed
    } else {
        // Roster buttons (only shown when lineups are not loaded)
        const loadRosterButtons = gamesContainer.querySelectorAll('.load-roster-btn');
        loadRosterButtons.forEach(button => {
            button.addEventListener('click', function() {
                const gameId = this.getAttribute('data-game-id');
                loadRosterForGame(gameId, this);
            });
        });
        
        // Scores buttons (available even without lineups)
        // Scores are loaded automatically when odds load
    }

    // Update live status/time from CDN after rendering
    updateLiveInfoForGames(games);
    startLiveBoxscorePolling();
}

// Create game card with lineups
function createGameCard(game, hasLineups = false) {
    const card = document.createElement('div');
    card.className = 'game-card';
    card.setAttribute('data-game-id', game.game_id || '');
    card.setAttribute('data-away-team', game.away_team || '');
    card.setAttribute('data-home-team', game.home_team || '');
    
    const gameDate = game.game_date || game.lineup_date || 'N/A';
    const gameTime = game.game_time || 'N/A';
    const lineups = game.lineups || {};
    
    // Check if scores are available
    const hasScores = (game.home_score !== null && game.home_score !== undefined) || 
                      (game.away_score !== null && game.away_score !== undefined);
    const awayScore = game.away_score !== null && game.away_score !== undefined ? game.away_score : '';
    const homeScore = game.home_score !== null && game.home_score !== undefined ? game.home_score : '';
    const scoreDisplay = hasScores ? `${awayScore} - ${homeScore}` : 'VS';
    
    // Check game status
    const isCompleted = game.game_completed === 1 || game.game_completed === true;
    const gameStatus = hasScores ? (isCompleted ? 'TERMINADO' : 'LIVE') : '';
    const statusClass = isCompleted ? 'game-status-completed' : 'game-status-live';
    
    card.innerHTML = `
        <div class="game-header">
            <div class="game-info">
                <div class="game-date-time">
                    ${formatDate(gameDate)} - ${formatTime(gameTime, gameDate)}
                    ${gameStatus ? `<span class="game-status ${statusClass}">${gameStatus}</span>` : ''}
                </div>
                <div class="game-live-info" data-game-id="${game.game_id || ''}"></div>
                <div class="teams">
                    <div class="team team-away">
                        <span class="team-name">${game.away_team_name || game.away_team}</span>
                        <img src="${game.away_team_logo_url || getPlaceholderLogo()}" 
                             alt="${game.away_team_name || game.away_team}" 
                             class="team-logo"
                             onerror="this.src='${getPlaceholderLogo()}'">
                    </div>
                    <div class="game-center">
                        <div class="game-center-status" data-game-id="${game.game_id || ''}"></div>
                        <span class="vs">${scoreDisplay}</span>
                    </div>
                    <div class="team team-home">
                        <img src="${game.home_team_logo_url || getPlaceholderLogo()}" 
                             alt="${game.home_team_name || game.home_team}" 
                             class="team-logo"
                             onerror="this.src='${getPlaceholderLogo()}'">
                        <span class="team-name">${game.home_team_name || game.home_team}</span>
                    </div>
                </div>
            </div>
            ${hasLineups ? '<button class="expand-toggle-btn" data-game-id="' + game.game_id + '" onclick="toggleGameCard(this)" title="Expandir/Retraer"><span class="expand-icon">▼</span></button>' : ''}
        </div>
        
        <div class="actions-section">
            ${!hasLineups ? '<button class="action-btn load-roster-btn" data-game-id="' + game.game_id + '"><span class="btn-text">Cargar Roster</span></button>' : ''}
            ${hasLineups ? '<div class="game-logs-controls"><button class="action-btn select-all-players-btn" data-game-id="' + game.game_id + '"><span class="btn-text">Seleccionar Todos</span></button><button class="action-btn load-game-logs-btn" data-game-id="' + game.game_id + '"><span class="btn-text">Cargar Game Logs (<span class="selected-count">0</span>)</span></button></div><button class="action-btn load-odds-btn" data-game-id="' + game.game_id + '">Cargar Odds</button>' : ''}
        </div>
        ${hasLineups ? `
        <div class="lineups-section collapsed">
                ${createLineupsHTML(lineups, game.away_team, game.away_team_name, game.away_team_logo_url, game.game_id)}
                ${createLineupsHTML(lineups, game.home_team, game.home_team_name, game.home_team_logo_url, game.game_id)}
        </div>
        ` : ''}
    `;
    
    return card;
}

// Create lineups HTML
function createLineupsHTML(lineups, teamAbbr, teamName, teamLogoUrl, gameId) {
    if (!lineups || !lineups[teamAbbr]) {
        return `
            <div class="team-lineup">
                <div class="team-lineup-header">
                    <span class="team-name-text">${teamName || teamAbbr}</span>
                </div>
                <div class="no-lineup">Lineup no disponible</div>
            </div>
        `;
    }
    
    const teamLineup = lineups[teamAbbr];
    const positions = ['PG', 'SG', 'SF', 'PF', 'C'];
    
    // Sort positions by value (players with value first) while maintaining position labels
    const positionsWithValue = positions.map(position => {
        const player = teamLineup[position];
        if (!player) {
            return { position, valuePriority: 0, originalIndex: positions.indexOf(position) };
        }
        const valueInfo = calculatePlayerValuePriority(player);
        return { 
            position, 
            valuePriority: valueInfo.priority,
            originalIndex: positions.indexOf(position)
        };
    }).sort((a, b) => {
        // First sort by value (higher priority first)
        if (b.valuePriority !== a.valuePriority) {
            return b.valuePriority - a.valuePriority;
        }
        // If same value, maintain original position order
        return a.originalIndex - b.originalIndex;
    }).map(p => p.position);
    
    // Get starters (players with positions) - ordered by value
    const startersHTML = positionsWithValue.map(position => {
        const player = teamLineup[position];
        if (!player) {
            return `
                <div class="position-card">
                    <div class="position-label">${position}</div>
                    <div class="no-lineup">N/A</div>
                    <div class="player-stats-placeholder">
                        <div class="player-points empty">-</div>
                        <div class="player-assists empty">-</div>
                        <div class="player-rebounds empty">-</div>
                    </div>
                    <span class="status-badge starter">STARTER</span>
                </div>
            `;
        }
        
        const playerStatus = player.player_status || 'STARTER';
        const statusBadge = playerStatus === 'STARTER' 
            ? '<span class="status-badge starter">STARTER</span>' 
            : '<span class="status-badge bench">BENCH</span>';
        
        // Use calculatePlayerValuePriority to get consistent value calculation
        const valueInfo = calculatePlayerValuePriority(player);
        const cardValueClass = valueInfo.cardValueClass || '';
        const highestValueIndicator = valueInfo.highestValueIndicator;
        
        // Only highlight the line with the highest value
        const shouldHighlightPts = highestValueIndicator && highestValueIndicator.type === 'PTS';
        const shouldHighlightAst = highestValueIndicator && highestValueIndicator.type === 'AST';
        const shouldHighlightReb = highestValueIndicator && highestValueIndicator.type === 'REB';
        
        // Always show stats lines, even if empty, to maintain symmetry
        const pointsDirection = getSuggestedDirection(player, 'points');
        const assistsDirection = getSuggestedDirection(player, 'assists');
        const reboundsDirection = getSuggestedDirection(player, 'rebounds');
        const pointsLine = player.points_line !== null && player.points_line !== undefined 
            ? `<div class="player-points ${shouldHighlightPts ? 'has-value' : ''}">${player.points_line} pts ${renderSuggestionArrow(pointsDirection)}</div>` 
            : '<div class="player-points empty">-</div>';
        const assistsLine = player.assists_line !== null && player.assists_line !== undefined 
            ? `<div class="player-assists ${shouldHighlightAst ? 'has-value' : ''}">${player.assists_line} ast ${renderSuggestionArrow(assistsDirection)}</div>` 
            : '<div class="player-assists empty">-</div>';
        const reboundsLine = player.rebounds_line !== null && player.rebounds_line !== undefined 
            ? `<div class="player-rebounds ${shouldHighlightReb ? 'has-value' : ''}">${player.rebounds_line} reb ${renderSuggestionArrow(reboundsDirection)}</div>` 
            : '<div class="player-rebounds empty">-</div>';
        
        const playerId = player.player_id || '';
        const statusClass = playerStatus === 'STARTER' ? 'is-starter' : 'is-bench';
        return `
            <div class="position-card ${cardValueClass} ${statusClass}" data-player-id="${playerId}" data-player-name="${player.player_name}">
                <div class="position-label">${position}</div>
                ${playerId ? `<input type="checkbox" class="player-game-log-checkbox" data-player-id="${playerId}" data-player-name="${player.player_name}" title="Seleccionar para cargar game logs">` : ''}
                <img src="${player.player_photo_url || getPlaceholderPlayer()}" 
                     alt="${player.player_name}" 
                     class="player-photo"
                     onerror="this.src='${getPlaceholderPlayer()}'">
                <div class="player-name">${player.player_name}</div>
                ${pointsLine}
                ${assistsLine}
                ${reboundsLine}
                <div class="player-live-stats">Live: -</div>
                ${statusBadge}
                ${playerId ? `<button class="show-game-logs-btn" data-player-id="${playerId}" onclick="toggleGameLogs(${playerId}, this)">Ver Últimos Juegos</button>` : ''}
            </div>
        `;
    }).join('');
    
    // Get BENCH players (now stored as array under 'BENCH' key)
    const benchPlayers = [];
    if (teamLineup['BENCH']) {
        if (Array.isArray(teamLineup['BENCH'])) {
            benchPlayers.push(...teamLineup['BENCH']);
        } else {
            benchPlayers.push(teamLineup['BENCH']);
        }
    }
    
    const benchPlayersWithOdds = benchPlayers.filter(player => (
        player.points_line !== null && player.points_line !== undefined
    ) || (
        player.assists_line !== null && player.assists_line !== undefined
    ) || (
        player.rebounds_line !== null && player.rebounds_line !== undefined
    ));
    
    // Sort bench players by value (players with value first)
    const sortedBenchPlayers = benchPlayersWithOdds.map(player => {
        const valueInfo = calculatePlayerValuePriority(player);
        return { player, valuePriority: valueInfo.priority };
    }).sort((a, b) => b.valuePriority - a.valuePriority).map(item => item.player);
    
    const benchHTML = sortedBenchPlayers.map(player => {
        // Use calculatePlayerValuePriority to get consistent value calculation
        const valueInfo = calculatePlayerValuePriority(player);
        const cardValueClass = valueInfo.cardValueClass || '';
        const highestValueIndicator = valueInfo.highestValueIndicator;
        
        // Only highlight the line with the highest value
        const shouldHighlightPts = highestValueIndicator && highestValueIndicator.type === 'PTS';
        const shouldHighlightAst = highestValueIndicator && highestValueIndicator.type === 'AST';
        const shouldHighlightReb = highestValueIndicator && highestValueIndicator.type === 'REB';
        
        // Always show stats lines, even if empty, to maintain symmetry
        const pointsDirection = getSuggestedDirection(player, 'points');
        const assistsDirection = getSuggestedDirection(player, 'assists');
        const reboundsDirection = getSuggestedDirection(player, 'rebounds');
        const pointsLine = player.points_line !== null && player.points_line !== undefined 
            ? `<div class="player-points ${shouldHighlightPts ? 'has-value' : ''}">${player.points_line} pts ${renderSuggestionArrow(pointsDirection)}</div>` 
            : '<div class="player-points empty">-</div>';
        const assistsLine = player.assists_line !== null && player.assists_line !== undefined 
            ? `<div class="player-assists ${shouldHighlightAst ? 'has-value' : ''}">${player.assists_line} ast ${renderSuggestionArrow(assistsDirection)}</div>` 
            : '<div class="player-assists empty">-</div>';
        const reboundsLine = player.rebounds_line !== null && player.rebounds_line !== undefined 
            ? `<div class="player-rebounds ${shouldHighlightReb ? 'has-value' : ''}">${player.rebounds_line} reb ${renderSuggestionArrow(reboundsDirection)}</div>` 
            : '<div class="player-rebounds empty">-</div>';
        
        const playerId = player.player_id || '';
        return `
            <div class="position-card bench-card ${cardValueClass} is-bench" data-player-id="${playerId}" data-player-name="${player.player_name}">
                <div class="position-label">BENCH</div>
                ${playerId ? `<input type="checkbox" class="player-game-log-checkbox" data-player-id="${playerId}" data-player-name="${player.player_name}" title="Seleccionar para cargar game logs">` : ''}
                <img src="${player.player_photo_url || getPlaceholderPlayer()}" 
                     alt="${player.player_name}" 
                     class="player-photo"
                     onerror="this.src='${getPlaceholderPlayer()}'">
                <div class="player-name">${player.player_name}</div>
                ${pointsLine}
                ${assistsLine}
                ${reboundsLine}
                <div class="player-live-stats">Live: -</div>
                <span class="status-badge bench">BENCH</span>
                ${playerId ? `<button class="show-game-logs-btn" data-player-id="${playerId}" onclick="toggleGameLogs(${playerId}, this)">Ver Últimos Juegos</button>` : ''}
            </div>
        `;
    }).join('');
    
    // Only show team logo in header if we have lineup data
    const showTeamHeader = lineups && lineups[teamAbbr];
    
    return `
        <div class="team-lineup" data-team-abbr="${teamAbbr}">
            ${showTeamHeader ? `
            <div class="team-lineup-header">
                <span class="team-name-text">${teamName || teamAbbr}</span>
                <button class="team-toggle-btn" data-team-abbr="${teamAbbr}" onclick="toggleTeamLineup(this)" title="Expandir/Retraer equipo">
                    <span class="team-toggle-icon">▼</span>
                </button>
            </div>
            ` : ''}
            <div class="team-lineup-content">
                <div class="positions-grid">
                    ${startersHTML}
                </div>
                ${benchHTML ? `<div class="bench-players"><div class="bench-players-grid">${benchHTML}</div></div>` : ''}
            </div>
        </div>
    `;
}

function getPlaceholderPlayer() {
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9IiNkZGQiLz48Y2lyY2xlIGN4PSI0MCIgY3k9IjMwIiByPSIxMCIgZmlsbD0iIzk5OSIvPjxwYXRoIGQ9Ik0yMCA1MHEwIDIwIDIwIDIwaDIwcTIwIDAgMjAgLTIwIiBmaWxsPSIjOTk5Ii8+PC9zdmc+';
}

// Utility functions
function formatDate(dateString) {
    if (!dateString || dateString === 'N/A') return 'N/A';
    try {
        // Parse date manually to avoid timezone issues
        // Expected format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
        let year, month, day;
        if (dateString.includes(' ')) {
            // Format: YYYY-MM-DD HH:MM:SS
            const datePart = dateString.split(' ')[0];
            [year, month, day] = datePart.split('-').map(Number);
        } else {
            // Format: YYYY-MM-DD
            [year, month, day] = dateString.split('-').map(Number);
        }
        
        // Create date in local timezone (not UTC)
        const date = new Date(year, month - 1, day);
        return date.toLocaleDateString('es-ES', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    } catch (e) {
        console.error('Error formatting date:', dateString, e);
        return dateString;
    }
}

function formatTime(timeString, dateString = null) {
    if (!timeString || timeString === 'N/A') return 'N/A';
    try {
        // If we have both date and time, convert from Mexico City time to Tijuana timezone
        if (dateString && dateString !== 'N/A') {
            try {
                // Parse the time string
                const timePart = timeString.split('.')[0]; // Remove microseconds if present
                const timeParts = timePart.split(':');
                const hours = timeParts[0] || '00';
                const minutes = timeParts[1] || '00';
                const seconds = timeParts[2] || '00';
                
                // Create a date string assuming the time is in Mexico City timezone
                // We'll create a date object and use timezone conversion
                // The trick: create date in UTC by manually calculating the offset
                // Mexico City is UTC-6 in standard time, UTC-5 in daylight time
                // We'll assume UTC-6 for simplicity (or we could detect DST)
                
                // Better approach: Create date assuming it's in Mexico City, then convert to Tijuana
                // We'll use a workaround: create the date as if it's UTC, then adjust
                
                // Create ISO string
                const isoString = `${dateString}T${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:${seconds.padStart(2, '0')}`;
                
                // Create a date object - this will be interpreted in local time
                // We need to convert from Mexico City to Tijuana
                // The proper way: use a timezone-aware approach
                
                // Practical solution: Use Intl to format
                // First, we need to create a date that represents the time in Mexico City
                // Since Date() doesn't accept timezone, we'll use a workaround:
                // 1. Get current time in Mexico City for the date
                // 2. Calculate the difference
                // 3. Adjust and format in Tijuana
                
                // Simpler: Assume the time difference is constant (2 hours)
                // Tijuana is typically 2 hours behind Mexico City
                // This works for most cases, though DST transitions might cause minor issues
                
                let hourInt = parseInt(hours);
                let minuteInt = parseInt(minutes);
                
                // Tijuana is 2 hours behind Mexico City
                // Subtract 2 hours
                hourInt = hourInt - 2;
                if (hourInt < 0) {
                    hourInt = hourInt + 24;
                }
                
                return `${String(hourInt).padStart(2, '0')}:${String(minuteInt).padStart(2, '0')}`;
            } catch (e) {
                console.warn('Error converting time to Tijuana timezone, using original:', e);
                // Fallback to original format
                const [hours, minutes] = timeString.split(':');
                return `${hours}:${minutes}`;
            }
        }
        
        // Fallback: just format the time string
        const [hours, minutes] = timeString.split(':');
        return `${hours}:${minutes}`;
    } catch (e) {
        return timeString;
    }
}

function getPlaceholderLogo() {
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5OQkE8L3RleHQ+PC9zdmc+';
}

// Calculate value level based on OVER/UNDER percentage
function calculateValueLevel(overCount, underCount, totalGames) {
    if (!totalGames || totalGames === 0) {
        return { level: 'none', percentage: 0, class: '', indicator: '' };
    }
    
    // Calculate the maximum percentage between OVER and UNDER
    const overPercentage = (overCount / totalGames) * 100;
    const underPercentage = (underCount / totalGames) * 100;
    const maxPercentage = Math.max(overPercentage, underPercentage);
    
    // Determine value level
    let level, classSuffix, indicator;
    
    if (maxPercentage >= 90) {
        level = 'highest';
        classSuffix = 'value-highest';
        indicator = '🔥'; // Fire emoji for highest value
    } else if (maxPercentage >= 80) {
        level = 'very-high';
        classSuffix = 'value-very-high';
        indicator = '⭐'; // Star for very high value
    } else if (maxPercentage >= 70) {
        level = 'high';
        classSuffix = 'value-high';
        indicator = '✨'; // Sparkles for high value
    } else if (maxPercentage >= 60) {
        level = 'medium';
        classSuffix = 'value-medium';
        indicator = '💡'; // Light bulb for medium value
    } else {
        level = 'none';
        classSuffix = '';
        indicator = '';
    }
    
    return {
        level: level,
        percentage: maxPercentage,
        class: classSuffix,
        indicator: indicator,
        overPercentage: overPercentage,
        underPercentage: underPercentage
    };
}

// Calculate player value priority for sorting (higher number = higher priority)
function calculatePlayerValuePriority(player) {
    if (!player || !player.over_under_history) {
        return { priority: 0, cardValueClass: '', highestValueIndicator: null };
    }
    
    const history = player.over_under_history;
    
    // Defensive check: If no game logs available or invalid data, no value can be calculated
    const totalGames = history.total_games || 0;
    if (!totalGames || totalGames === 0 || typeof totalGames !== 'number' || isNaN(totalGames)) {
        return { priority: 0, cardValueClass: '', highestValueIndicator: null };
    }
    
    let valueIndicators = [];
    
    // Check points value - only if we have points_line and game logs
    if (player.points_line !== null && player.points_line !== undefined && 
        totalGames > 0 && typeof totalGames === 'number' && !isNaN(totalGames)) {
        const overCount = history.over_count || 0;
        const underCount = history.under_count || 0;
        
        // Additional validation: over_count + under_count should not exceed total_games significantly
        if (overCount + underCount <= totalGames * 1.1) { // Allow 10% margin for pushes
            const valueLevel = calculateValueLevel(overCount, underCount, totalGames);
            if (valueLevel.level !== 'none') {
                valueIndicators.push({ type: 'PTS', ...valueLevel });
            }
        }
    }
    
    // Check assists value - only if we have game logs (total_games > 0)
    if (player.assists_line !== null && player.assists_line !== undefined && 
        totalGames > 0 &&
        history.assists_over_count !== undefined && history.assists_under_count !== undefined) {
        const assistsOver = history.assists_over_count;
        const assistsUnder = history.assists_under_count;
        // Additional validation: assists counts should not exceed total_games significantly
        if (assistsOver + assistsUnder <= totalGames * 1.1) {
            const valueLevel = calculateValueLevel(assistsOver, assistsUnder, totalGames);
            if (valueLevel.level !== 'none') {
                valueIndicators.push({ type: 'AST', ...valueLevel });
            }
        }
    }
    
    // Check rebounds value - only if we have game logs (total_games > 0)
    if (player.rebounds_line !== null && player.rebounds_line !== undefined && 
        totalGames > 0 &&
        history.rebounds_over_count !== undefined && history.rebounds_under_count !== undefined) {
        const reboundsOver = history.rebounds_over_count;
        const reboundsUnder = history.rebounds_under_count;
        // Additional validation: rebounds counts should not exceed total_games significantly
        if (reboundsOver + reboundsUnder <= totalGames * 1.1) {
            const valueLevel = calculateValueLevel(reboundsOver, reboundsUnder, totalGames);
            if (valueLevel.level !== 'none') {
                valueIndicators.push({ type: 'REB', ...valueLevel });
            }
        }
    }
    
    if (valueIndicators.length === 0) {
        return { priority: 0, cardValueClass: '', highestValueIndicator: null };
    }
    
    // Find the highest value indicator
    // Priority: First by level (highest > very-high > high > medium), then by percentage
    const levelPriority = { 'highest': 4, 'very-high': 3, 'high': 2, 'medium': 1, 'none': 0 };
    const highestValueIndicator = valueIndicators.reduce((max, indicator) => {
        const maxPriority = levelPriority[max.level] || 0;
        const indicatorPriority = levelPriority[indicator.level] || 0;
        
        // First compare by level priority (higher level wins)
        if (indicatorPriority > maxPriority) {
            return indicator;
        } else if (indicatorPriority < maxPriority) {
            return max;
        } else {
            // If same level, compare by percentage (higher percentage wins)
            if (indicator.percentage > max.percentage) {
                return indicator;
            }
            return max;
        }
    }, valueIndicators[0]);
    
    // Calculate priority: level priority * 1000 + percentage (for sorting)
    const priority = (levelPriority[highestValueIndicator.level] || 0) * 1000 + highestValueIndicator.percentage;
    
    // Debug logging
    console.log(`[calculatePlayerValuePriority] Player: ${player.player_name || 'Unknown'}, Indicators:`, valueIndicators.map(i => `${i.type}: ${i.level} (${i.percentage.toFixed(1)}%)`).join(', '), 'Highest:', highestValueIndicator.type, 'Class:', highestValueIndicator.class);
    
    return {
        priority: priority,
        cardValueClass: highestValueIndicator.class,
        highestValueIndicator: highestValueIndicator
    };
}

function showLoading() {
    loadingDiv.classList.remove('hidden');
}

function hideLoading() {
    loadingDiv.classList.add('hidden');
}

// Show loading overlay on a specific game card
function showGameCardLoading(gameCard) {
    if (!gameCard) return;
    
    // Check if overlay already exists
    let overlay = gameCard.querySelector('.game-card-loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'game-card-loading-overlay';
        overlay.innerHTML = `
            <div class="game-card-loading-spinner"></div>
            <div class="game-card-loading-text">Cargando odds...</div>
        `;
        gameCard.style.position = 'relative';
        gameCard.appendChild(overlay);
    }
    overlay.classList.add('active');
}

// Hide loading overlay on a specific game card
function hideGameCardLoading(gameCard) {
    if (!gameCard) return;
    
    const overlay = gameCard.querySelector('.game-card-loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function hideError() {
    errorDiv.classList.add('hidden');
}

function showSuccess(message) {
    // Create or get success message div
    let successDiv = document.getElementById('success-message');
    if (!successDiv) {
        successDiv = document.createElement('div');
        successDiv.id = 'success-message';
        successDiv.className = 'success-message';
        successDiv.style.cssText = 'background-color: #d4edda; color: #155724; padding: 12px; margin: 10px 0; border-radius: 4px; border: 1px solid #c3e6cb;';
        const header = document.querySelector('header');
        if (header) {
            header.appendChild(successDiv);
        }
    }
    successDiv.textContent = message;
    successDiv.classList.remove('hidden');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        successDiv.classList.add('hidden');
    }, 5000);
}

function showEmptyState(message) {
    gamesContainer.innerHTML = `
        <div class="empty-state">
            <h2>📋 Sin juegos</h2>
            <p>${message}</p>
        </div>
    `;
}

// Open game logs modal
window.toggleGameLogs = async function(playerId, buttonElement) {
    // Get player name and lines from the card
    const playerCard = buttonElement.closest('.position-card') || buttonElement.closest('.value-player-card');
    const playerName = playerCard ? playerCard.querySelector('.player-name')?.textContent : `Player ${playerId}`;
    const pointsLineElement = playerCard ? playerCard.querySelector('.player-points') : null;
    const pointsLine = pointsLineElement ? parseFloat(pointsLineElement.textContent.replace(' pts', '')) : null;
    const assistsLineElement = playerCard ? playerCard.querySelector('.player-assists') : null;
    const assistsLine = assistsLineElement ? parseFloat(assistsLineElement.textContent.replace(' ast', '')) : null;
    const reboundsLineElement = playerCard ? playerCard.querySelector('.player-rebounds') : null;
    const reboundsLine = reboundsLineElement ? parseFloat(reboundsLineElement.textContent.replace(' reb', '')) : null;
    
    // Create or get modal
    let modal = document.getElementById('game-logs-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'game-logs-modal';
        modal.className = 'game-logs-modal';
        modal.innerHTML = `
            <div class="game-logs-modal-overlay"></div>
            <div class="game-logs-modal-content">
                <div class="game-logs-modal-header">
                    <h3 class="game-logs-modal-title">Últimos Juegos</h3>
                    <button class="game-logs-modal-close" onclick="closeGameLogsModal()">&times;</button>
                </div>
                <div class="modal-tabs">
                    <button class="modal-tab active" data-tab="game-logs" onclick="switchModalTab('game-logs')">Últimos Juegos</button>
                    <button class="modal-tab" data-tab="odds-history" onclick="switchModalTab('odds-history')">Histórico de Odds</button>
                    <button class="modal-tab" data-tab="simulator" onclick="switchModalTab('simulator')">Simulador</button>
                </div>
                <div class="game-logs-modal-body">
                    <div class="game-logs-loading">Cargando...</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close on overlay click
        modal.querySelector('.game-logs-modal-overlay').addEventListener('click', closeGameLogsModal);
        
        // Close on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeGameLogsModal();
            }
        });
    }
    
    // Update player name in modal (no lines in title)
    const titleElement = modal.querySelector('.game-logs-modal-title');
    if (titleElement) {
        titleElement.textContent = playerName;
    }
    
    // Get game_id from the player card if available
    const gameCard = buttonElement.closest('.game-card');
    const gameId = gameCard ? gameCard.getAttribute('data-game-id') : null;
    const liveSummaryPromise = fetchLivePlayerSummary(playerId, gameId);
    
    // Show modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // Load game logs
    const modalBody = modal.querySelector('.game-logs-modal-body');
    modalBody.setAttribute('data-player-id', playerId);
    if (gameId) {
        modalBody.setAttribute('data-game-id', gameId);
    }
    modalBody.setAttribute('data-has-points-line', pointsLine !== null && !isNaN(pointsLine) ? 'true' : 'false');
    modalBody.setAttribute('data-assists-line', assistsLine !== null && !isNaN(assistsLine) ? assistsLine.toString() : '');
    modalBody.setAttribute('data-rebounds-line', reboundsLine !== null && !isNaN(reboundsLine) ? reboundsLine.toString() : '');
    modalBody.innerHTML = '<div class="game-logs-loading">Cargando...</div>';
    
    // Clear cached content when loading new player
    cachedGameLogsContent = null;
    cachedOddsHistoryData = null;
    cachedGameLogsData = null;
    
    // Reset to game-logs tab
    const tabs = modal.querySelectorAll('.modal-tab');
    tabs.forEach(tab => {
        if (tab.getAttribute('data-tab') === 'game-logs') {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    try {
        // Load both game logs and odds history in parallel
        const [gameLogsResponse, oddsHistoryResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/nba/players/${playerId}/game-logs${playerName ? `?player_name=${encodeURIComponent(playerName)}` : ''}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            }),
            fetch(`${API_BASE_URL}/nba/players/${playerId}/odds-history${gameId ? `?game_id=${gameId}&limit=200` : '?limit=200'}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            })
        ]);
        
        if (!gameLogsResponse.ok) {
            throw new Error(`HTTP ${gameLogsResponse.status}`);
        }
        
        const gameLogsData = await gameLogsResponse.json();
        let oddsHistoryData = null;
        
        if (oddsHistoryResponse.ok) {
            const oddsData = await oddsHistoryResponse.json();
            if (oddsData.success && oddsData.odds_history) {
                oddsHistoryData = oddsData.odds_history;
            }
        }
        
        // Create a map of odds history by game_date for quick lookup
        const oddsByDate = new Map();
        if (oddsHistoryData && oddsHistoryData.length > 0) {
            oddsHistoryData.forEach(odds => {
                if (odds.game_date) {
                    // Normalize date format for matching (YYYY-MM-DD)
                    const dateKey = odds.game_date.split('T')[0]; // Remove time if present
                    if (!oddsByDate.has(dateKey)) {
                        oddsByDate.set(dateKey, []);
                    }
                    oddsByDate.get(dateKey).push(odds);
                }
            });
        }
        
        // Helper function to find odds for a specific game date
        const findOddsForDate = (gameDate) => {
            const dateKey = gameDate.split('T')[0]; // Normalize to YYYY-MM-DD
            const oddsList = oddsByDate.get(dateKey);
            if (oddsList && oddsList.length > 0) {
                // Return the most recent odds for that date (first in list since it's sorted DESC)
                return oddsList[0];
            }
            return null;
        };
        
        if (gameLogsData.success && gameLogsData.game_logs && gameLogsData.game_logs.length > 0) {
            // Store raw game logs data for simulator
            cachedGameLogsData = gameLogsData.game_logs;
            
            // Sort by date descending (most recent first)
            const sortedGames = [...gameLogsData.game_logs].sort((a, b) => {
                const dateA = new Date(a.game_date);
                const dateB = new Date(b.game_date);
                return dateB - dateA;
            });
            
            // Reorganize game logs by stat type (Puntos, Asistencias, Rebotes)
            // Match each game with its historical odds if available
            const gamesData = sortedGames.map(game => {
                const gameDate = formatGameLogDate(game.game_date);
                const minutes = game.minutes_played !== null && game.minutes_played !== undefined
                    ? parseFloat(game.minutes_played)
                    : null;
                const starterStatus = game.starter_status || (game.start_position ? 'STARTER' : null);
                const startPosition = game.start_position !== null && game.start_position !== undefined
                    ? String(game.start_position).trim()
                    : null;
                const points = game.points !== null && game.points !== undefined 
                    ? parseFloat(game.points) 
                    : null;
                const assists = game.assists !== null && game.assists !== undefined 
                    ? parseInt(game.assists) 
                    : null;
                const rebounds = game.rebounds !== null && game.rebounds !== undefined 
                    ? parseInt(game.rebounds) 
                    : null;
                
                // Find historical odds for this game date
                const historicalOdds = findOddsForDate(game.game_date);
                
                return {
                    date: gameDate,
                    rawDate: game.game_date,
                    minutes: minutes,
                    starterStatus: starterStatus,
                    startPosition: startPosition || null,
                    points: points,
                    assists: assists,
                    rebounds: rebounds,
                    historicalOdds: historicalOdds // Add historical odds to each game
                };
            });
            
            // Prepare data for each stat type with value calculations
            // Use historical odds when available, fallback to current line
            const tabsData = [];
            
            // Points Tab - check if we have any historical odds or current line
            const hasPointsData = oddsHistoryData && oddsHistoryData.some(o => o.points_line !== null) || (pointsLine !== null && !isNaN(pointsLine));
            if (hasPointsData) {
                const pointsGames = gamesData.filter(g => g.points !== null);
                const pointsResults = pointsGames.map(game => {
                    // Use historical odds line if available, otherwise use current line
                    const line = game.historicalOdds && game.historicalOdds.points_line !== null 
                        ? game.historicalOdds.points_line 
                        : (pointsLine !== null && !isNaN(pointsLine) ? pointsLine : null);
                    
                    if (line === null) {
                        return null; // Skip games without a line
                    }
                    
                    const result = game.points > line ? 'OVER' : (game.points < line ? 'UNDER' : 'PUSH');
                    return { ...game, result: result, statType: 'points', statValue: game.points, line: line, hasHistoricalLine: !!game.historicalOdds };
                }).filter(g => g !== null); // Remove null entries
                
                if (pointsResults.length > 0) {
                    const pointsOver = pointsResults.filter(g => g.result === 'OVER').length;
                    const pointsUnder = pointsResults.filter(g => g.result === 'UNDER').length;
                    const pointsPush = pointsResults.filter(g => g.result === 'PUSH').length;
                    const totalGames = pointsResults.length;
                    
                    // Calculate value level for points
                    const pointsValueLevel = calculateValueLevel(pointsOver, pointsUnder, totalGames);
                    
                    // Use current line for display if no historical data, otherwise use average or most common
                    const displayLine = pointsLine !== null && !isNaN(pointsLine) ? pointsLine : 
                        (pointsResults.length > 0 ? pointsResults[0].line : null);
                    
                    tabsData.push({
                        type: 'points',
                        label: 'Puntos',
                        valueLevel: pointsValueLevel,
                        results: pointsResults,
                        over: pointsOver,
                        under: pointsUnder,
                        push: pointsPush,
                        total: totalGames,
                        line: displayLine
                    });
                }
            }
            
            // Assists Tab
            const hasAssistsData = oddsHistoryData && oddsHistoryData.some(o => o.assists_line !== null) || (assistsLine !== null && !isNaN(assistsLine));
            if (hasAssistsData) {
                const assistsGames = gamesData.filter(g => g.assists !== null);
                const assistsResults = assistsGames.map(game => {
                    // Use historical odds line if available, otherwise use current line
                    const line = game.historicalOdds && game.historicalOdds.assists_line !== null 
                        ? game.historicalOdds.assists_line 
                        : (assistsLine !== null && !isNaN(assistsLine) ? assistsLine : null);
                    
                    if (line === null) {
                        return null; // Skip games without a line
                    }
                    
                    const result = game.assists > line ? 'OVER' : (game.assists < line ? 'UNDER' : 'PUSH');
                    return { ...game, result: result, statType: 'assists', statValue: game.assists, line: line, hasHistoricalLine: !!game.historicalOdds };
                }).filter(g => g !== null);
                
                if (assistsResults.length > 0) {
                    const assistsOver = assistsResults.filter(g => g.result === 'OVER').length;
                    const assistsUnder = assistsResults.filter(g => g.result === 'UNDER').length;
                    const assistsPush = assistsResults.filter(g => g.result === 'PUSH').length;
                    const totalGames = assistsResults.length;
                    
                    // Calculate value level for assists
                    const assistsValueLevel = calculateValueLevel(assistsOver, assistsUnder, totalGames);
                    
                    const displayLine = assistsLine !== null && !isNaN(assistsLine) ? assistsLine : 
                        (assistsResults.length > 0 ? assistsResults[0].line : null);
                    
                    tabsData.push({
                        type: 'assists',
                        label: 'Asistencias',
                        valueLevel: assistsValueLevel,
                        results: assistsResults,
                        over: assistsOver,
                        under: assistsUnder,
                        push: assistsPush,
                        total: totalGames,
                        line: displayLine
                    });
                }
            }
            
            // Rebounds Tab
            const hasReboundsData = oddsHistoryData && oddsHistoryData.some(o => o.rebounds_line !== null) || (reboundsLine !== null && !isNaN(reboundsLine));
            if (hasReboundsData) {
                const reboundsGames = gamesData.filter(g => g.rebounds !== null);
                const reboundsResults = reboundsGames.map(game => {
                    // Use historical odds line if available, otherwise use current line
                    const line = game.historicalOdds && game.historicalOdds.rebounds_line !== null 
                        ? game.historicalOdds.rebounds_line 
                        : (reboundsLine !== null && !isNaN(reboundsLine) ? reboundsLine : null);
                    
                    if (line === null) {
                        return null; // Skip games without a line
                    }
                    
                    const result = game.rebounds > line ? 'OVER' : (game.rebounds < line ? 'UNDER' : 'PUSH');
                    return { ...game, result: result, statType: 'rebounds', statValue: game.rebounds, line: line, hasHistoricalLine: !!game.historicalOdds };
                }).filter(g => g !== null);
                
                if (reboundsResults.length > 0) {
                    const reboundsOver = reboundsResults.filter(g => g.result === 'OVER').length;
                    const reboundsUnder = reboundsResults.filter(g => g.result === 'UNDER').length;
                    const reboundsPush = reboundsResults.filter(g => g.result === 'PUSH').length;
                    const totalGames = reboundsResults.length;
                    
                    // Calculate value level for rebounds
                    const reboundsValueLevel = calculateValueLevel(reboundsOver, reboundsUnder, totalGames);
                    
                    const displayLine = reboundsLine !== null && !isNaN(reboundsLine) ? reboundsLine : 
                        (reboundsResults.length > 0 ? reboundsResults[0].line : null);
                    
                    tabsData.push({
                        type: 'rebounds',
                        label: 'Rebotes',
                        valueLevel: reboundsValueLevel,
                        results: reboundsResults,
                        over: reboundsOver,
                        under: reboundsUnder,
                        push: reboundsPush,
                        total: totalGames,
                        line: displayLine
                    });
                }
            }
            
            if (tabsData.length > 0) {
                // Create tabs HTML with value-based styling
                const tabsHTML = tabsData.map((tab, index) => {
                    const valueClass = tab.valueLevel.class || '';
                    const isActive = index === 0 ? 'active' : '';
                    return `
                        <button class="game-logs-stat-tab ${isActive} ${valueClass}" 
                                data-stat-type="${tab.type}" 
                                onclick="switchGameLogsStatTab('${tab.type}')">
                            ${tab.label}
                        </button>
                    `;
                }).join('');
                
                // Create tab content HTML
                const tabContentsHTML = tabsData.map((tab, index) => {
                    const isActive = index === 0 ? 'active' : '';
                    const statLabel = tab.type === 'points' ? 'Puntos' : (tab.type === 'assists' ? 'Asistencias' : 'Rebotes');
                    const statColumn = tab.type === 'points' ? 'Puntos' : (tab.type === 'assists' ? 'Asistencias' : 'Rebotes');
                    
                    // Calculate probabilities
                    const overProbability = tab.total > 0 ? ((tab.over / tab.total) * 100).toFixed(1) : '0.0';
                    const underProbability = tab.total > 0 ? ((tab.under / tab.total) * 100).toFixed(1) : '0.0';
                    
                    return `
                        <div class="game-logs-stat-tab-content ${isActive}" id="game-logs-${tab.type}">
                            <div class="value-section-summary">
                                <div class="summary-item">
                                    <span class="summary-label">Total:</span>
                                    <span class="summary-value">${tab.total}</span>
                                </div>
                                <div class="summary-item">
                                    <span class="summary-label">OVER:</span>
                                    <span class="summary-value over">${tab.over}</span>
                                    <span class="summary-probability">(${overProbability}%)</span>
                                </div>
                                <div class="summary-item">
                                    <span class="summary-label">UNDER:</span>
                                    <span class="summary-value under">${tab.under}</span>
                                    <span class="summary-probability">(${underProbability}%)</span>
                                </div>
                                ${tab.push > 0 ? `
                                <div class="summary-item">
                                    <span class="summary-label">PUSH:</span>
                                    <span class="summary-value push">${tab.push}</span>
                                </div>
                                ` : ''}
                                <div class="summary-item">
                                    <span class="summary-label">Línea:</span>
                                    <span class="summary-value">${tab.line.toFixed(1)}</span>
                                </div>
                            </div>
                            <table class="game-logs-table">
                                <thead>
                                    <tr>
                                        <th>Fecha</th>
                                        <th>MIN</th>
                                        <th>${statColumn}</th>
                                        <th>Rol</th>
                                        <th>Línea</th>
                                        <th>Resultado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tab.results.map(game => {
                                        const resultClass = game.result.toLowerCase();
                                        const minutesValue = game.minutes !== null && game.minutes !== undefined
                                            ? game.minutes.toFixed(1)
                                            : '-';
                                        const statValue = tab.type === 'points' ? game.points.toFixed(1) : (tab.type === 'assists' ? game.assists : game.rebounds);
                                        const roleLabel = game.starterStatus === 'STARTER' ? 'Titular' : (game.starterStatus === 'BENCH' ? 'Banca' : '-');
                                        const roleTitle = game.startPosition ? `Posición inicial: ${game.startPosition}` : '';
                                        // Show the line used for this specific game (historical if available)
                                        const gameLine = game.line !== null && game.line !== undefined ? game.line.toFixed(1) : 'N/A';
                                        const lineDisplay = gameLine !== 'N/A' ? gameLine : '-';
                                        const lineTitle = game.hasHistoricalLine ? `Línea histórica: ${gameLine}` : `Línea actual: ${gameLine}`;
                                        return `
                                            <tr class="game-log-row" data-stat-type="${tab.type}" data-result="${resultClass}">
                                                <td class="game-log-date-cell">${game.date}</td>
                                                <td class="game-log-minutes-cell">${minutesValue}</td>
                                                <td class="game-log-${tab.type}-cell">${statValue}</td>
                                                <td class="game-log-role-cell" title="${roleTitle}">${roleLabel}</td>
                                                <td class="game-log-line-cell" title="${lineTitle}">
                                                    ${lineDisplay}
                                                    ${game.hasHistoricalLine ? ' <span class="historical-line-indicator" title="Línea histórica">📊</span>' : ''}
                                                </td>
                                                <td class="game-log-result-cell">
                                                    <span class="result-badge ${resultClass}">${game.result}</span>
                                                </td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                }).join('');
                
                modalBody.innerHTML = `
                    <div class="game-logs-stat-tabs">
                        ${tabsHTML}
                    </div>
                    <div class="game-logs-stat-tabs-content">
                        ${tabContentsHTML}
                    </div>
                `;
                const liveSummary = await liveSummaryPromise;
                renderLivePlayerSummary(modalBody, liveSummary);
                cachedGameLogsContent = modalBody.innerHTML;
            } else {
                // No lines available, show basic stats
                const logsHTML = sortedGames.map(game => {
                    const gameDate = formatGameLogDate(game.game_date);
                    const minutes = game.minutes_played !== null && game.minutes_played !== undefined 
                        ? parseFloat(game.minutes_played).toFixed(1) 
                        : 'N/A';
                    const starterStatus = game.starter_status || (game.start_position ? 'STARTER' : null);
                    const roleLabel = starterStatus === 'STARTER' ? 'Titular' : (starterStatus === 'BENCH' ? 'Banca' : 'N/A');
                    const points = game.points !== null && game.points !== undefined 
                        ? parseFloat(game.points).toFixed(1) 
                        : 'N/A';
                    const assists = game.assists !== null && game.assists !== undefined 
                        ? parseInt(game.assists) 
                        : 'N/A';
                    const rebounds = game.rebounds !== null && game.rebounds !== undefined 
                        ? parseInt(game.rebounds) 
                        : 'N/A';
                    
                    return `
                        <div class="game-log-item">
                            <div class="game-log-date">${gameDate}</div>
                            <div class="game-log-stats">
                                <div class="game-log-stat">
                                    <span class="stat-label">MIN</span>
                                    <span class="stat-value">${minutes}</span>
                                </div>
                                <div class="game-log-stat">
                                    <span class="stat-label">ROL</span>
                                    <span class="stat-value">${roleLabel}</span>
                                </div>
                                <div class="game-log-stat">
                                    <span class="stat-label">PTS</span>
                                    <span class="stat-value">${points}</span>
                                </div>
                                <div class="game-log-stat">
                                    <span class="stat-label">AST</span>
                                    <span class="stat-value">${assists}</span>
                                </div>
                                <div class="game-log-stat">
                                    <span class="stat-label">REB</span>
                                    <span class="stat-value">${rebounds}</span>
                                </div>
                            </div>
                </div>
            `;
                }).join('');
                
                modalBody.innerHTML = `
                    <div class="game-logs-list">
                        ${logsHTML}
            </div>
        `;
                const liveSummary = await liveSummaryPromise;
                renderLivePlayerSummary(modalBody, liveSummary);
                cachedGameLogsContent = modalBody.innerHTML;
            }
        } else {
            modalBody.innerHTML = '<div class="no-game-logs">No hay game logs disponibles para este jugador.</div>';
            const liveSummary = await liveSummaryPromise;
            renderLivePlayerSummary(modalBody, liveSummary);
            cachedGameLogsContent = modalBody.innerHTML;
        }
    } catch (error) {
        console.error(`Error loading game logs for player ${playerId}:`, error);
        modalBody.innerHTML = '<div class="no-game-logs">Error al cargar game logs</div>';
    }
};

// Close game logs modal
window.closeGameLogsModal = function() {
    const modal = document.getElementById('game-logs-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        // Clear cached content
        cachedGameLogsContent = null;
        cachedOddsHistoryData = null;
        cachedGameLogsData = null;
    }
};

// Switch game logs stat tab
window.switchGameLogsStatTab = function(statType) {
    const modal = document.getElementById('game-logs-modal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.game-logs-modal-body');
    if (!modalBody) return;
    
    // Update tab buttons
    const tabs = modalBody.querySelectorAll('.game-logs-stat-tab');
    tabs.forEach(tab => {
        if (tab.getAttribute('data-stat-type') === statType) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Update tab content
    const contents = modalBody.querySelectorAll('.game-logs-stat-tab-content');
    contents.forEach(content => {
        if (content.id === `game-logs-${statType}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
};

// Filter function removed - always show all results

// Store original game logs content
let cachedGameLogsContent = null;
let cachedGameLogsData = null; // Store raw game logs data for simulator

// Switch modal tab
window.switchModalTab = function(tabName) {
    const modal = document.getElementById('game-logs-modal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.game-logs-modal-body');
    if (!modalBody) return;
    
    // Update tab buttons
    const tabs = modal.querySelectorAll('.modal-tab');
    tabs.forEach(tab => {
        if (tab.getAttribute('data-tab') === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Show/hide filters based on tab
    const filtersSection = modal.querySelector('#game-logs-filters');
    
    if (tabName === 'game-logs') {
        // Restore cached game logs content
        if (cachedGameLogsContent) {
            modalBody.innerHTML = cachedGameLogsContent;
        }
    } else if (tabName === 'odds-history') {
        // Load odds history
        loadOddsHistory();
    } else if (tabName === 'simulator') {
        // Load simulator
        loadSimulator();
    }
};

// Store odds history data globally
let cachedOddsHistoryData = null;

// Load odds history
async function loadOddsHistory() {
    const modal = document.getElementById('game-logs-modal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.game-logs-modal-body');
    const playerId = modalBody.getAttribute('data-player-id');
    const gameId = modalBody.getAttribute('data-game-id');
    
    if (!playerId) {
        modalBody.innerHTML = '<div class="no-game-logs">No se pudo obtener el ID del jugador</div>';
        return;
    }
    
    // If we have cached data, use it; otherwise load from API
    if (cachedOddsHistoryData) {
        renderOddsHistoryTabs(cachedOddsHistoryData);
        return;
    }
    
    modalBody.innerHTML = '<div class="game-logs-loading">Cargando histórico de odds...</div>';
    
    try {
        const url = new URL(`${API_BASE_URL}/nba/players/${playerId}/odds-history`);
        if (gameId) {
            url.searchParams.append('game_id', gameId);
        }
        url.searchParams.append('limit', '200');
        
        const response = await fetch(url.toString(), {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.odds_history && data.odds_history.length > 0) {
            cachedOddsHistoryData = data.odds_history;
            renderOddsHistoryTabs(data.odds_history);
        } else {
            modalBody.innerHTML = '<div class="no-game-logs">No hay histórico de odds disponible para este jugador.</div>';
        }
    } catch (error) {
        console.error(`Error loading odds history for player ${playerId}:`, error);
        modalBody.innerHTML = '<div class="no-game-logs">Error al cargar histórico de odds</div>';
    }
}

// Render odds history with tabs
function renderOddsHistoryTabs(oddsHistory) {
    const modal = document.getElementById('game-logs-modal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.game-logs-modal-body');
    
    // Separate data by type
    const pointsHistory = oddsHistory.filter(entry => entry.points_line !== null && entry.points_line !== undefined);
    const assistsHistory = oddsHistory.filter(entry => entry.assists_line !== null && entry.assists_line !== undefined);
    const reboundsHistory = oddsHistory.filter(entry => entry.rebounds_line !== null && entry.rebounds_line !== undefined);
    
    // Create tabs HTML
    const tabsHTML = `
        <div class="odds-history-tabs">
            <button class="odds-history-tab active" data-odds-type="points" onclick="switchOddsHistoryTab('points')">
                Puntos ${pointsHistory.length > 0 ? `(${pointsHistory.length})` : ''}
            </button>
            <button class="odds-history-tab" data-odds-type="assists" onclick="switchOddsHistoryTab('assists')">
                Asistencias ${assistsHistory.length > 0 ? `(${assistsHistory.length})` : ''}
            </button>
            <button class="odds-history-tab" data-odds-type="rebounds" onclick="switchOddsHistoryTab('rebounds')">
                Rebotes ${reboundsHistory.length > 0 ? `(${reboundsHistory.length})` : ''}
            </button>
                </div>
        <div class="odds-history-content">
            <div class="odds-history-tab-content active" id="odds-history-points">
                ${renderOddsHistoryTable(pointsHistory, 'points')}
            </div>
            <div class="odds-history-tab-content" id="odds-history-assists">
                ${renderOddsHistoryTable(assistsHistory, 'assists')}
            </div>
            <div class="odds-history-tab-content" id="odds-history-rebounds">
                ${renderOddsHistoryTable(reboundsHistory, 'rebounds')}
                </div>
                </div>
            `;
    
    modalBody.innerHTML = tabsHTML;
}

// Render odds history table for a specific type
function renderOddsHistoryTable(history, type) {
    if (!history || history.length === 0) {
        return '<div class="no-game-logs">No hay histórico disponible para este tipo.</div>';
        }
        
        return `
        <table class="game-logs-table">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Línea</th>
                    <th>Over Odds</th>
                    <th>Under Odds</th>
                </tr>
            </thead>
            <tbody>
                ${history.map(entry => {
                    // Format time in Los Angeles timezone
                    // Debug: log the original date string
                    if (entry.recorded_at) {
                        console.log('Original recorded_at:', entry.recorded_at, 'Parsed Date:', new Date(entry.recorded_at));
                    }
                    const timeStr = formatTimeInLATimezone(entry.recorded_at);
                    
                    let lineValue;
                    if (type === 'points') {
                        lineValue = entry.points_line;
                    } else if (type === 'assists') {
                        lineValue = entry.assists_line;
                    } else if (type === 'rebounds') {
                        lineValue = entry.rebounds_line;
    }
    
    return `
                        <tr>
                            <td class="game-log-date-cell">${timeStr}</td>
                            <td class="game-log-line-cell">${lineValue ? lineValue.toFixed(1) : 'N/A'}</td>
                            <td>${entry.over_odds ? formatOdds(entry.over_odds) : 'N/A'}</td>
                            <td>${entry.under_odds ? formatOdds(entry.under_odds) : 'N/A'}</td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

// Switch odds history tab
window.switchOddsHistoryTab = function(type) {
    const modal = document.getElementById('game-logs-modal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.game-logs-modal-body');
    
    // Update tab buttons
    const tabs = modalBody.querySelectorAll('.odds-history-tab');
    tabs.forEach(tab => {
        if (tab.getAttribute('data-odds-type') === type) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Update tab content
    const contents = modalBody.querySelectorAll('.odds-history-tab-content');
    contents.forEach(content => {
        if (content.id === `odds-history-${type}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
};

// Load simulator
function loadSimulator() {
    const modal = document.getElementById('game-logs-modal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.game-logs-modal-body');
    
    if (!cachedGameLogsData || cachedGameLogsData.length === 0) {
        modalBody.innerHTML = '<div class="no-game-logs">No hay game logs disponibles para simular.</div>';
        return;
    }
    
    // Sort games by date descending (most recent first)
    const sortedGames = [...cachedGameLogsData].sort((a, b) => {
        const dateA = new Date(a.game_date);
        const dateB = new Date(b.game_date);
        return dateB - dateA;
    });
    
    // Limit to top 25 games
    const topGames = sortedGames.slice(0, 25);
    
    // Prepare games data
    const gamesData = topGames.map(game => {
        const gameDate = formatGameLogDate(game.game_date);
        const points = game.points !== null && game.points !== undefined 
            ? parseFloat(game.points) 
            : null;
        const assists = game.assists !== null && game.assists !== undefined 
            ? parseInt(game.assists) 
            : null;
        const rebounds = game.rebounds !== null && game.rebounds !== undefined 
            ? parseInt(game.rebounds) 
            : null;
        
        return {
            date: gameDate,
            rawDate: game.game_date,
            points: points,
            assists: assists,
            rebounds: rebounds
        };
    });
    
    // Create simulator interface
    modalBody.innerHTML = `
        <div class="simulator-container">
            <div class="simulator-inputs">
                <div class="simulator-input-group">
                    <label for="simulator-points-line">Línea de Puntos:</label>
                    <input type="number" id="simulator-points-line" step="0.5" placeholder="Ej: 10.5" 
                           onkeypress="if(event.key === 'Enter') calculateSimulator('points')" />
                    <button class="simulator-calculate-btn" onclick="calculateSimulator('points')">Calcular</button>
                </div>
                <div class="simulator-input-group">
                    <label for="simulator-assists-line">Línea de Asistencias:</label>
                    <input type="number" id="simulator-assists-line" step="0.5" placeholder="Ej: 5.5" 
                           onkeypress="if(event.key === 'Enter') calculateSimulator('assists')" />
                    <button class="simulator-calculate-btn" onclick="calculateSimulator('assists')">Calcular</button>
                </div>
                <div class="simulator-input-group">
                    <label for="simulator-rebounds-line">Línea de Rebotes:</label>
                    <input type="number" id="simulator-rebounds-line" step="0.5" placeholder="Ej: 8.5" 
                           onkeypress="if(event.key === 'Enter') calculateSimulator('rebounds')" />
                    <button class="simulator-calculate-btn" onclick="calculateSimulator('rebounds')">Calcular</button>
                </div>
            </div>
            <div class="simulator-results" id="simulator-results">
                <div class="simulator-placeholder">
                    <p>Ingresa una línea y haz clic en "Calcular" o presiona Enter para ver los resultados</p>
                    <p class="simulator-info">Basado en los últimos ${topGames.length} juegos disponibles</p>
                </div>
            </div>
        </div>
    `;
    
    // Store games data in a data attribute for the calculate function
    modalBody.setAttribute('data-simulator-games', JSON.stringify(gamesData));
}

// Calculate simulator results
window.calculateSimulator = function(statType) {
    const modal = document.getElementById('game-logs-modal');
    if (!modal) return;
    
    const modalBody = modal.querySelector('.game-logs-modal-body');
    const gamesDataJson = modalBody.getAttribute('data-simulator-games');
    
    if (!gamesDataJson) {
        return;
    }
    
    const gamesData = JSON.parse(gamesDataJson);
    const lineInput = document.getElementById(`simulator-${statType}-line`);
    const line = lineInput ? parseFloat(lineInput.value) : null;
    
    if (line === null || isNaN(line)) {
        alert('Por favor ingresa una línea válida');
        return;
    }
    
    // Filter games with valid stat data
    const validGames = gamesData.filter(g => g[statType] !== null && g[statType] !== undefined);
    
    if (validGames.length === 0) {
        alert(`No hay datos de ${statType === 'points' ? 'puntos' : statType === 'assists' ? 'asistencias' : 'rebotes'} disponibles`);
        return;
    }
    
    // Calculate results
    const results = validGames.map(game => {
        const statValue = game[statType];
        const result = statValue > line ? 'OVER' : (statValue < line ? 'UNDER' : 'PUSH');
        return { ...game, result: result, statValue: statValue, line: line };
    });
    
    const overCount = results.filter(g => g.result === 'OVER').length;
    const underCount = results.filter(g => g.result === 'UNDER').length;
    const pushCount = results.filter(g => g.result === 'PUSH').length;
    const totalGames = results.length;
    
    // Calculate percentages
    const overPercentage = totalGames > 0 ? ((overCount / totalGames) * 100).toFixed(1) : '0.0';
    const underPercentage = totalGames > 0 ? ((underCount / totalGames) * 100).toFixed(1) : '0.0';
    
    // Calculate value level
    const valueLevel = calculateValueLevel(overCount, underCount, totalGames);
    
    // Determine which result has value
    const maxPercentage = Math.max(parseFloat(overPercentage), parseFloat(underPercentage));
    const hasValue = maxPercentage >= 60;
    const valueDirection = parseFloat(overPercentage) > parseFloat(underPercentage) ? 'OVER' : 'UNDER';
    
    // Create results HTML
    const statLabel = statType === 'points' ? 'Puntos' : (statType === 'assists' ? 'Asistencias' : 'Rebotes');
    const statColumn = statType === 'points' ? 'Puntos' : (statType === 'assists' ? 'Asistencias' : 'Rebotes');
    
    const resultsHTML = `
        <div class="simulator-result-section">
            <div class="value-section-summary">
                <div class="summary-item">
                    <span class="summary-label">Total:</span>
                    <span class="summary-value">${totalGames}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">OVER:</span>
                    <span class="summary-value over">${overCount}</span>
                    <span class="summary-probability">(${overPercentage}%)</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">UNDER:</span>
                    <span class="summary-value under">${underCount}</span>
                    <span class="summary-probability">(${underPercentage}%)</span>
                </div>
                ${pushCount > 0 ? `
                <div class="summary-item">
                    <span class="summary-label">PUSH:</span>
                    <span class="summary-value push">${pushCount}</span>
                </div>
                ` : ''}
                <div class="summary-item">
                    <span class="summary-label">Línea Simulada:</span>
                    <span class="summary-value">${line.toFixed(1)}</span>
                </div>
                ${hasValue ? `
                <div class="summary-item ${valueLevel.class}">
                    <span class="summary-label">Valor:</span>
                    <span class="summary-value">${valueLevel.indicator || ''} ${valueDirection} ${maxPercentage}%</span>
                </div>
                ` : ''}
            </div>
            <table class="game-logs-table">
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>${statColumn}</th>
                        <th>Línea</th>
                        <th>Resultado</th>
                    </tr>
                </thead>
                <tbody>
                    ${results.map(game => {
                        const resultClass = game.result.toLowerCase();
                        const statValue = statType === 'points' ? game.points.toFixed(1) : (statType === 'assists' ? game.assists : game.rebounds);
                        return `
                            <tr class="game-log-row" data-stat-type="${statType}" data-result="${resultClass}">
                                <td class="game-log-date-cell">${game.date}</td>
                                <td class="game-log-${statType}-cell">${statValue}</td>
                                <td class="game-log-line-cell">${game.line.toFixed(1)}</td>
                                <td class="game-log-result-cell">
                                    <span class="result-badge ${resultClass}">${game.result}</span>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    // Update results section
    const resultsContainer = document.getElementById('simulator-results');
    if (resultsContainer) {
        resultsContainer.innerHTML = resultsHTML;
    }
};

// Format odds (American format)
function formatOdds(odds) {
    if (odds === null || odds === undefined) return 'N/A';
    if (odds > 0) {
        return `+${odds}`;
    }
    return odds.toString();
}

// Format date for game log display
function formatGameLogDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
}

// Show value legend modal
window.showValueLegend = function() {
    // Create or get modal
    let modal = document.getElementById('value-legend-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'value-legend-modal';
        modal.className = 'value-legend-modal';
        modal.innerHTML = `
            <div class="value-legend-overlay" onclick="closeValueLegend()"></div>
            <div class="value-legend-content">
                <div class="value-legend-header">
                    <h3>Leyenda de Valores</h3>
                    <button class="value-legend-close" onclick="closeValueLegend()">&times;</button>
                </div>
                <div class="value-legend-body">
                    <p class="value-legend-description">
                        Las tarjetas de jugadores se resaltan según el porcentaje de veces que se ha cumplido el OVER o UNDER en sus últimos 25 juegos.
                    </p>
                    <div class="value-legend-items">
                        <div class="value-legend-item">
                            <div class="value-legend-sample value-highest-sample">
                                <div class="value-indicator">🔥</div>
                            </div>
                            <div class="value-legend-info">
                                <div class="value-legend-title">Mayor Valor 🔥</div>
                                <div class="value-legend-range">90% - 100%</div>
                                <div class="value-legend-desc">Muy alta probabilidad. Oportunidad de valor máxima con animación.</div>
                            </div>
                        </div>
                        <div class="value-legend-item">
                            <div class="value-legend-sample value-very-high-sample">
                                <div class="value-indicator">⭐</div>
                            </div>
                            <div class="value-legend-info">
                                <div class="value-legend-title">Muy Probable ⭐</div>
                                <div class="value-legend-range">80% - 89%</div>
                                <div class="value-legend-desc">Alta probabilidad. Buena oportunidad de valor.</div>
                            </div>
                        </div>
                        <div class="value-legend-item">
                            <div class="value-legend-sample value-high-sample">
                                <div class="value-indicator">✨</div>
                            </div>
                            <div class="value-legend-info">
                                <div class="value-legend-title">Probable ✨</div>
                                <div class="value-legend-range">70% - 79%</div>
                                <div class="value-legend-desc">Probabilidad moderada-alta. Oportunidad de valor.</div>
                            </div>
                        </div>
                        <div class="value-legend-item">
                            <div class="value-legend-sample value-medium-sample">
                                <div class="value-indicator">💡</div>
                            </div>
                            <div class="value-legend-info">
                                <div class="value-legend-title">Menos Probable 💡</div>
                                <div class="value-legend-range">60% - 69%</div>
                                <div class="value-legend-desc">Probabilidad moderada. Oportunidad de valor menor.</div>
                            </div>
                        </div>
                        <div class="value-legend-item">
                            <div class="value-legend-sample value-none-sample">
                            </div>
                            <div class="value-legend-info">
                                <div class="value-legend-title">Sin Resaltado</div>
                                <div class="value-legend-range">&lt; 60%</div>
                                <div class="value-legend-desc">Probabilidad baja. Sin oportunidad de valor significativa.</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeValueLegend();
            }
        });
    }
    
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
};

// Close value legend modal
window.closeValueLegend = function() {
    const modal = document.getElementById('value-legend-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
};

// Switch between views (tabs)
window.switchView = function(viewName) {
    // Update tab buttons
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        if (tab.getAttribute('data-view') === viewName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Show/hide view sections
    if (viewName === 'lineups') {
        lineupsView.classList.remove('hidden');
        lineupsView.classList.add('active');
        valuePlayersView.classList.add('hidden');
        valuePlayersView.classList.remove('active');
        lineupsActions.classList.remove('hidden');
    } else if (viewName === 'value-players') {
        lineupsView.classList.add('hidden');
        lineupsView.classList.remove('active');
        valuePlayersView.classList.remove('hidden');
        valuePlayersView.classList.add('active');
        lineupsActions.classList.add('hidden');
        // Load value players when switching to this view
        loadValuePlayers();
    }
};

// Load all players with value from all games (using cached data if available)
async function loadValuePlayers() {
    valuePlayersContainer.innerHTML = '';
    
    // Use cached games data if available (no HTTP call needed)
    let gamesData = cachedGamesData;
    
    // Only make HTTP call if we don't have cached data
    if (!gamesData || gamesData.length === 0) {
        const today = getTodayInLATimezone();
        
        // Show loading only if we need to fetch data
        loadingText.textContent = 'Cargando jugadores con valor...';
        showLoading();
        hideError();
        
        try {
            // Get all games with lineups for today
            const response = await fetch(`${API_BASE_URL}/nba/lineups?date=${today}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Error ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.games && data.games.length > 0) {
                gamesData = data.games;
                // Cache the data for future use
                cachedGamesData = gamesData;
            } else {
                valuePlayersContainer.innerHTML = `
                    <div class="empty-state">
                        <h2>📋 Sin jugadores con valor</h2>
                        <p>No hay jugadores con valor disponibles. Asegúrate de haber cargado los odds para los juegos de hoy.</p>
                    </div>
                `;
                hideLoading();
                return;
            }
        } catch (error) {
            console.error('Error loading value players:', error);
            showError(`Error al cargar jugadores con valor: ${error.message || error}`);
            hideLoading();
            return;
        }
    }
    
    // Process games data (from cache or fresh fetch)
    try {
        if (gamesData && gamesData.length > 0) {
            // Extract all players with value from all games
            const playersWithValue = [];
            
            gamesData.forEach(game => {
                if (!game.lineups) return;
                
                // Process each team's lineup
                Object.keys(game.lineups).forEach(teamAbbr => {
                    const teamLineup = game.lineups[teamAbbr];
                    const positions = ['PG', 'SG', 'SF', 'PF', 'C'];
                    
                    // Process starters
                    positions.forEach(position => {
                        const player = teamLineup[position];
                        if (player && player.over_under_history && player.over_under_history.total_games > 0) {
                            const valueInfo = calculatePlayerValuePriority(player);
                            if (valueInfo.priority > 0) {
                                playersWithValue.push({
                                    ...player,
                                    position: position,
                                    team: teamAbbr,
                                    teamName: game[`${teamAbbr === game.away_team ? 'away' : 'home'}_team_name`] || teamAbbr,
                                    gameId: game.game_id,
                                    gameDate: game.game_date,
                                    gameTime: game.game_time,
                                    opponent: teamAbbr === game.away_team ? game.home_team_name : game.away_team_name,
                                    valuePriority: valueInfo.priority,
                                    valueClass: valueInfo.cardValueClass,
                                    status: 'STARTER'
                                });
                            }
                        }
                    });
                    
                    // Process bench players
                    if (teamLineup['BENCH']) {
                        const benchPlayers = Array.isArray(teamLineup['BENCH']) 
                            ? teamLineup['BENCH'] 
                            : [teamLineup['BENCH']];
                        
                        benchPlayers.forEach(player => {
                            if (player && player.over_under_history && player.over_under_history.total_games > 0) {
                                const valueInfo = calculatePlayerValuePriority(player);
                                if (valueInfo.priority > 0) {
                                    playersWithValue.push({
                                        ...player,
                                        position: 'BENCH',
                                        team: teamAbbr,
                                        teamName: game[`${teamAbbr === game.away_team ? 'away' : 'home'}_team_name`] || teamAbbr,
                                        gameId: game.game_id,
                                        gameDate: game.game_date,
                                        gameTime: game.game_time,
                                        opponent: teamAbbr === game.away_team ? game.home_team_name : game.away_team_name,
                                        valuePriority: valueInfo.priority,
                                        valueClass: valueInfo.cardValueClass,
                                        status: 'BENCH'
                                    });
                                }
                            }
                        });
                    }
                });
            });
            
            // Sort by value priority (highest first)
            playersWithValue.sort((a, b) => b.valuePriority - a.valuePriority);
            
            // Display players
            displayValuePlayers(playersWithValue);
        } else {
            valuePlayersContainer.innerHTML = `
                <div class="empty-state">
                    <h2>📋 Sin jugadores con valor</h2>
                    <p>No hay jugadores con valor disponibles. Asegúrate de haber cargado los odds para los juegos de hoy.</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Error loading value players:', error);
        showError(`Error al cargar jugadores con valor: ${error.message || error}`);
    } finally {
        hideLoading();
    }
}

// Display players with value
function displayValuePlayers(players) {
    if (players.length === 0) {
        valuePlayersContainer.innerHTML = `
            <div class="empty-state">
                <h2>📋 Sin jugadores con valor</h2>
                <p>No hay jugadores con valor disponibles. Asegúrate de haber cargado los odds para los juegos de hoy.</p>
            </div>
        `;
        return;
    }
    
    const playersHTML = players.map(player => {
        const valueIndicators = [];
        const history = player.over_under_history;
        
        // Calculate which stats have value
        if (history.total_games > 0) {
            const overCount = history.over_count || 0;
            const underCount = history.under_count || 0;
            const valueLevel = calculateValueLevel(overCount, underCount, history.total_games);
            if (valueLevel.level !== 'none') {
                valueIndicators.push({ type: 'PTS', ...valueLevel });
            }
        }
        
        if (player.assists_line !== null && player.assists_line !== undefined && 
            history.assists_over_count !== undefined && history.assists_under_count !== undefined) {
            const assistsOver = history.assists_over_count;
            const assistsUnder = history.assists_under_count;
            const valueLevel = calculateValueLevel(assistsOver, assistsUnder, history.total_games);
            if (valueLevel.level !== 'none') {
                valueIndicators.push({ type: 'AST', ...valueLevel });
            }
        }
        
        if (player.rebounds_line !== null && player.rebounds_line !== undefined && 
            history.rebounds_over_count !== undefined && history.rebounds_under_count !== undefined) {
            const reboundsOver = history.rebounds_over_count;
            const reboundsUnder = history.rebounds_under_count;
            const valueLevel = calculateValueLevel(reboundsOver, reboundsUnder, history.total_games);
            if (valueLevel.level !== 'none') {
                valueIndicators.push({ type: 'REB', ...valueLevel });
            }
        }
        
        // Find highest value indicator
        const levelPriority = { 'highest': 4, 'very-high': 3, 'high': 2, 'medium': 1, 'none': 0 };
        const highestValueIndicator = valueIndicators.length > 0 ? valueIndicators.reduce((max, indicator) => {
            if (indicator.percentage > max.percentage) {
                return indicator;
            } else if (indicator.percentage === max.percentage) {
                const maxPriority = levelPriority[max.level] || 0;
                const indicatorPriority = levelPriority[indicator.level] || 0;
                return indicatorPriority > maxPriority ? indicator : max;
            }
            return max;
        }, valueIndicators[0]) : null;
        
        const shouldHighlightPts = highestValueIndicator && highestValueIndicator.type === 'PTS';
        const shouldHighlightAst = highestValueIndicator && highestValueIndicator.type === 'AST';
        const shouldHighlightReb = highestValueIndicator && highestValueIndicator.type === 'REB';
        
        const pointsLine = player.points_line !== null && player.points_line !== undefined 
            ? `<div class="player-points ${shouldHighlightPts ? 'has-value' : ''}">${player.points_line} pts</div>` 
            : '<div class="player-points empty">-</div>';
        const assistsLine = player.assists_line !== null && player.assists_line !== undefined 
            ? `<div class="player-assists ${shouldHighlightAst ? 'has-value' : ''}">${player.assists_line} ast</div>` 
            : '<div class="player-assists empty">-</div>';
        const reboundsLine = player.rebounds_line !== null && player.rebounds_line !== undefined 
            ? `<div class="player-rebounds ${shouldHighlightReb ? 'has-value' : ''}">${player.rebounds_line} reb</div>` 
            : '<div class="player-rebounds empty">-</div>';
        
        const playerId = player.player_id || '';
        const statusBadge = player.status === 'STARTER' 
            ? '<span class="status-badge starter">STARTER</span>' 
            : '<span class="status-badge bench">BENCH</span>';
        
        return `
            <div class="value-player-card ${player.valueClass}" data-player-id="${playerId}" data-player-name="${player.player_name}">
                <div class="value-player-header">
                    <div class="value-player-team-info">
                        <span class="value-player-team">${player.teamName}</span>
                        <span class="value-player-position">${player.position}</span>
                    </div>
                    <div class="value-player-game-info">
                        <span class="value-player-opponent">vs ${player.opponent}</span>
                        <span class="value-player-time">${formatTime(player.gameTime)}</span>
                    </div>
                </div>
                <img src="${player.player_photo_url || getPlaceholderPlayer()}" 
                     alt="${player.player_name}" 
                     class="player-photo"
                     onerror="this.src='${getPlaceholderPlayer()}'">
                <div class="player-name">${player.player_name}</div>
                ${pointsLine}
                ${assistsLine}
                ${reboundsLine}
                ${statusBadge}
                ${playerId ? `<button class="show-game-logs-btn" data-player-id="${playerId}" onclick="toggleGameLogs(${playerId}, this)">Ver Últimos Juegos</button>` : ''}
            </div>
        `;
    }).join('');
    
    valuePlayersContainer.innerHTML = `
        <div class="value-players-header">
            <h2>Jugadores con Valor (${players.length})</h2>
            <p class="value-players-subtitle">Jugadores ordenados por prioridad de valor de todos los juegos de hoy</p>
        </div>
        <div class="value-players-grid">
            ${playersHTML}
        </div>
    `;
}

// Expand game card (used when loading game logs or odds)
function expandGameCard(gameCard) {
    if (!gameCard) return;
    
    const lineupsSection = gameCard.querySelector('.lineups-section');
    const expandButton = gameCard.querySelector('.expand-toggle-btn');
    const expandIcon = expandButton ? expandButton.querySelector('.expand-icon') : null;
    
    if (lineupsSection) {
        lineupsSection.classList.remove('collapsed');
    }
    
    if (expandIcon) {
        expandIcon.textContent = '▲';
    }
}

// Toggle team lineup expand/collapse
window.toggleTeamLineup = function(buttonElement) {
    const teamLineup = buttonElement.closest('.team-lineup');
    if (!teamLineup) return;
    
    const teamContent = teamLineup.querySelector('.team-lineup-content');
    const toggleIcon = buttonElement.querySelector('.team-toggle-icon');
    
    if (!teamContent) return;
    
    // Toggle collapsed class
    const isCollapsed = teamContent.classList.contains('collapsed');
    if (isCollapsed) {
        teamContent.classList.remove('collapsed');
        if (toggleIcon) toggleIcon.textContent = '▼';
    } else {
        teamContent.classList.add('collapsed');
        if (toggleIcon) toggleIcon.textContent = '▶';
    }
};

// Toggle game card expand/collapse
window.toggleGameCard = function(buttonElement) {
    const gameCard = buttonElement.closest('.game-card');
    if (!gameCard) return;
    
    const lineupsSection = gameCard.querySelector('.lineups-section');
    const expandIcon = buttonElement.querySelector('.expand-icon');
    const actionsSection = gameCard.querySelector('.actions-section');
    
    if (!lineupsSection) return;
    
    // Toggle collapsed class
    const isCollapsed = lineupsSection.classList.contains('collapsed');
    
    if (isCollapsed) {
        // Expand
        lineupsSection.classList.remove('collapsed');
        if (expandIcon) {
            expandIcon.textContent = '▲';
        }
        // Show actions section if it exists
        if (actionsSection) {
            actionsSection.style.display = '';
        }
    } else {
        // Collapse
        lineupsSection.classList.add('collapsed');
        if (expandIcon) {
            expandIcon.textContent = '▼';
        }
    }
};

// Check schedule and load games on page load
window.addEventListener('DOMContentLoaded', () => {
    checkScheduleAndLoad();
    
    // Verify that loadOddsForGame is available globally
    if (typeof window.loadOddsForGame === 'undefined') {
        console.error('loadOddsForGame function is not defined in global scope!');
    } else {
        console.log('loadOddsForGame function is available');
    }
});
