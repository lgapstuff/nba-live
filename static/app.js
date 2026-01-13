// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const scheduleUploadSection = document.getElementById('schedule-upload-section');
const scheduleFileInput = document.getElementById('schedule-file-input');
// Depth chart file input removed - now loaded automatically from NBA API
const loadSchedulesBtn = document.getElementById('load-schedules-btn');
const lineupsActionsSection = document.getElementById('lineups-actions-section');
const loadLineupsBtn = document.getElementById('load-lineups-btn');
const loadingDiv = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const errorDiv = document.getElementById('error');
const gamesContainer = document.getElementById('games-container');

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

// Event Listeners
loadSchedulesBtn.addEventListener('click', () => {
    // Open file picker for schedule file
    scheduleFileInput.click();
});
scheduleFileInput.addEventListener('change', handleScheduleFileSelect);
loadLineupsBtn.addEventListener('click', loadLineups);

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
    
    // Show loading state on button
    const btnText = buttonElement.querySelector('.btn-text') || buttonElement;
    const originalText = btnText.textContent;
    btnText.textContent = 'Cargando...';
    buttonElement.disabled = true;
    
    try {
        console.log(`Loading game logs for game ${gameId} from ${API_BASE_URL}/nba/games/${gameId}/game-logs`);
        
        const response = await fetch(`${API_BASE_URL}/nba/games/${gameId}/game-logs`, {
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
        console.log('Game logs data received:', data);
        
        if (data.success) {
            console.log(`Game logs loaded successfully: ${data.players_processed} players, ${data.games_loaded} games`);
            showSuccess(`Game logs cargados: ${data.players_processed} jugadores, ${data.games_loaded} juegos`);
        } else {
            throw new Error(data.message || 'Error al cargar game logs');
        }
        
    } catch (error) {
        console.error('Error loading game logs for game:', error);
        showError(`Error al cargar game logs: ${error.message || error}`);
    } finally {
        // Restore button state
        btnText.textContent = originalText;
        buttonElement.disabled = false;
    }
};

// Load odds for a specific game (must be in global scope for onclick)
window.loadOddsForGame = async function(gameId, buttonElement) {
    console.log('loadOddsForGame called with gameId:', gameId);
    
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
    
    // Show loading state on button
    const btnText = buttonElement.querySelector('.btn-text') || buttonElement;
    const originalText = btnText.textContent;
    btnText.textContent = 'Cargando...';
    buttonElement.disabled = true;
    
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
            console.log('Odds loaded successfully, reloading games...');
            // Reload games with lineups to show updated BENCH players
            const today = getTodayInLATimezone();
            await loadGamesWithLineups(today);
        } else {
            throw new Error(data.message || 'Error al cargar odds');
        }
        
    } catch (error) {
        console.error('Error loading odds for game:', error);
        showError(`Error al cargar odds: ${error.message || error}`);
    } finally {
        // Restore button state
        btnText.textContent = originalText;
        buttonElement.disabled = false;
    }
};

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
        // Odds buttons
        const loadOddsButtons = gamesContainer.querySelectorAll('.load-odds-btn');
        loadOddsButtons.forEach(button => {
            button.addEventListener('click', function() {
                const gameId = this.getAttribute('data-game-id');
                loadOddsForGame(gameId, this);
            });
        });
    }
}

// Create game card with lineups
function createGameCard(game, hasLineups = false) {
    const card = document.createElement('div');
    card.className = 'game-card';
    
    const gameDate = game.game_date || game.lineup_date || 'N/A';
    const gameTime = game.game_time || 'N/A';
    const lineups = game.lineups || {};
    
    card.innerHTML = `
        <div class="game-header">
            <div class="game-info">
                <div class="game-date-time">${formatDate(gameDate)} - ${formatTime(gameTime)}</div>
                <div class="teams">
                    <div class="team">
                        <img src="${game.away_team_logo_url || getPlaceholderLogo()}" 
                             alt="${game.away_team_name || game.away_team}" 
                             class="team-logo"
                             onerror="this.src='${getPlaceholderLogo()}'">
                        <span class="team-name">${game.away_team_name || game.away_team}</span>
                    </div>
                    <span class="vs">VS</span>
                    <div class="team">
                        <img src="${game.home_team_logo_url || getPlaceholderLogo()}" 
                             alt="${game.home_team_name || game.home_team}" 
                             class="team-logo"
                             onerror="this.src='${getPlaceholderLogo()}'">
                        <span class="team-name">${game.home_team_name || game.home_team}</span>
                    </div>
                </div>
            </div>
        </div>
        
        ${hasLineups ? `
            <div class="actions-section">
                <button class="action-btn load-game-logs-btn" data-game-id="${game.game_id}">
                    Cargar Game Logs
                </button>
                <button class="action-btn load-odds-btn" data-game-id="${game.game_id}">
                    Cargar Odds
                </button>
            </div>
            <div class="lineups-section">
                <h3>Lineups</h3>
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
                    <img src="${teamLogoUrl || getPlaceholderLogo()}" 
                         alt="${teamName || teamAbbr}" 
                         class="team-logo"
                         onerror="this.src='${getPlaceholderLogo()}'">
                    <span class="team-name">${teamName || teamAbbr}</span>
                </div>
                <div class="no-lineup">Lineup no disponible</div>
            </div>
        `;
    }
    
    const teamLineup = lineups[teamAbbr];
    const positions = ['PG', 'SG', 'SF', 'PF', 'C'];
    
    // Get starters (players with positions)
    const startersHTML = positions.map(position => {
        const player = teamLineup[position];
        if (!player) {
            return `
                <div class="position-card">
                    <div class="position-label">${position}</div>
                    <div class="no-lineup">N/A</div>
                </div>
            `;
        }
        
        const playerStatus = player.player_status || 'STARTER';
        const statusBadge = playerStatus === 'STARTER' 
            ? '<span class="status-badge starter">STARTER</span>' 
            : '<span class="status-badge bench">BENCH</span>';
        
        const pointsLine = player.points_line !== null && player.points_line !== undefined 
            ? `<div class="player-points">${player.points_line} pts</div>` 
            : '';
        
        // Show OVER/UNDER history if available
        let overUnderHistory = '';
        if (player.over_under_history) {
            const history = player.over_under_history;
            const overCount = history.over_count || 0;
            const underCount = history.under_count || 0;
            const totalGames = history.total_games || 0;
            
            if (totalGames > 0) {
                overUnderHistory = `
                    <div class="over-under-history">
                        <div class="over-under-stats">
                            <span class="over-stat">OVER: ${overCount}/${totalGames}</span>
                            <span class="under-stat">UNDER: ${underCount}/${totalGames}</span>
                        </div>
                    </div>
                `;
            }
        }
        
        const playerId = player.player_id || '';
        return `
            <div class="position-card" data-player-id="${playerId}" data-player-name="${player.player_name}">
                <div class="position-label">${position}</div>
                <img src="${player.player_photo_url || getPlaceholderPlayer()}" 
                     alt="${player.player_name}" 
                     class="player-photo"
                     onerror="this.src='${getPlaceholderPlayer()}'">
                <div class="player-name">${player.player_name}</div>
                ${pointsLine}
                ${overUnderHistory}
                <div class="player-id">ID: ${playerId || 'N/A'}</div>
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
    
    const benchHTML = benchPlayers.map(player => {
        const pointsLine = player.points_line !== null && player.points_line !== undefined 
            ? `<div class="player-points">${player.points_line} pts</div>` 
            : '';
        
        // Show OVER/UNDER history if available
        let overUnderHistory = '';
        if (player.over_under_history) {
            const history = player.over_under_history;
            const overCount = history.over_count || 0;
            const underCount = history.under_count || 0;
            const totalGames = history.total_games || 0;
            
            if (totalGames > 0) {
                overUnderHistory = `
                    <div class="over-under-history">
                        <div class="over-under-stats">
                            <span class="over-stat">OVER: ${overCount}/${totalGames}</span>
                            <span class="under-stat">UNDER: ${underCount}/${totalGames}</span>
                        </div>
                    </div>
                `;
            }
        }
        
        const playerId = player.player_id || '';
        return `
            <div class="position-card bench-card" data-player-id="${playerId}" data-player-name="${player.player_name}">
                <div class="position-label">BENCH</div>
                <img src="${player.player_photo_url || getPlaceholderPlayer()}" 
                     alt="${player.player_name}" 
                     class="player-photo"
                     onerror="this.src='${getPlaceholderPlayer()}'">
                <div class="player-name">${player.player_name}</div>
                ${pointsLine}
                ${overUnderHistory}
                <div class="player-id">ID: ${playerId || 'N/A'}</div>
                <span class="status-badge bench">BENCH</span>
                ${playerId ? `<button class="show-game-logs-btn" data-player-id="${playerId}" onclick="toggleGameLogs(${playerId}, this)">Ver Últimos Juegos</button>` : ''}
            </div>
        `;
    }).join('');
    
    return `
        <div class="team-lineup">
            <div class="team-lineup-header">
                <img src="${teamLogoUrl || getPlaceholderLogo()}" 
                     alt="${teamName || teamAbbr}" 
                     class="team-logo"
                     onerror="this.src='${getPlaceholderLogo()}'">
                <span class="team-name">${teamName || teamAbbr}</span>
            </div>
            <div class="positions-grid">
                ${startersHTML}
            </div>
            ${benchHTML ? `<div class="bench-players"><h4>Jugadores BENCH</h4><div class="positions-grid">${benchHTML}</div></div>` : ''}
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

function formatTime(timeString) {
    if (!timeString || timeString === 'N/A') return 'N/A';
    try {
        const [hours, minutes] = timeString.split(':');
        return `${hours}:${minutes}`;
    } catch (e) {
        return timeString;
    }
}

function getPlaceholderLogo() {
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5OQkE8L3RleHQ+PC9zdmc+';
}

function showLoading() {
    loadingDiv.classList.remove('hidden');
}

function hideLoading() {
    loadingDiv.classList.add('hidden');
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
    // Get player name and points_line from the card
    const playerCard = buttonElement.closest('.position-card');
    const playerName = playerCard ? playerCard.querySelector('.player-name')?.textContent : `Player ${playerId}`;
    const pointsLineElement = playerCard ? playerCard.querySelector('.player-points') : null;
    const pointsLine = pointsLineElement ? parseFloat(pointsLineElement.textContent.replace(' pts', '')) : null;
    
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
    
    // Update player name and points line in modal
    const titleElement = modal.querySelector('.game-logs-modal-title');
    if (titleElement) {
        if (pointsLine !== null && !isNaN(pointsLine)) {
            titleElement.textContent = `${playerName} - Últimos Juegos (Línea: ${pointsLine} pts)`;
        } else {
            titleElement.textContent = `${playerName} - Últimos Juegos`;
        }
    }
    
    // Show modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // Load game logs
    const modalBody = modal.querySelector('.game-logs-modal-body');
    modalBody.innerHTML = '<div class="game-logs-loading">Cargando...</div>';
    
    try {
        const url = new URL(`${API_BASE_URL}/nba/players/${playerId}/game-logs`);
        if (playerName) {
            url.searchParams.append('player_name', playerName);
        }
        
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
        
        if (data.success && data.game_logs && data.game_logs.length > 0) {
            // Sort by date descending (most recent first)
            const sortedGames = [...data.game_logs].sort((a, b) => {
                const dateA = new Date(a.game_date);
                const dateB = new Date(b.game_date);
                return dateB - dateA;
            });
            
            // If points_line is available, show only OVER/UNDER
            if (pointsLine !== null && !isNaN(pointsLine)) {
                const logsHTML = sortedGames.map(game => {
                    const gameDate = formatGameLogDate(game.game_date);
                    const points = game.points !== null && game.points !== undefined 
                        ? parseFloat(game.points) 
                        : null;
                    
                    if (points === null) {
                        return '';
                    }
                    
                    const result = points > pointsLine ? 'OVER' : (points < pointsLine ? 'UNDER' : 'PUSH');
                    const resultClass = result === 'OVER' ? 'over' : (result === 'UNDER' ? 'under' : 'push');
                    
                    return `
                        <div class="game-log-item">
                            <div class="game-log-date">${gameDate}</div>
                            <div class="game-log-over-under">
                                <div class="game-log-points-display">
                                    <span class="points-value">${points.toFixed(1)}</span>
                                    <span class="points-vs">vs</span>
                                    <span class="points-line">${pointsLine.toFixed(1)}</span>
                                </div>
                                <div class="game-log-result ${resultClass}">
                                    ${result}
                                </div>
                            </div>
                        </div>
                    `;
                }).filter(html => html !== '').join('');
                
                modalBody.innerHTML = `
                    <div class="game-logs-list">
                        ${logsHTML}
                    </div>
                `;
            } else {
                // No points_line, show full stats
                const logsHTML = sortedGames.map(game => {
                    const gameDate = formatGameLogDate(game.game_date);
                    const minutes = game.minutes_played !== null && game.minutes_played !== undefined 
                        ? parseFloat(game.minutes_played).toFixed(1) 
                        : 'N/A';
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
            }
        } else {
            modalBody.innerHTML = '<div class="no-game-logs">No hay game logs disponibles para este jugador.</div>';
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
    }
};

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
