// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const dateInput = document.getElementById('date-input');
const loadGamesBtn = document.getElementById('load-games-btn');
const loadLineupsBtn = document.getElementById('load-lineups-btn');
const loadOddsBtn = document.getElementById('load-odds-btn');
const loadingDiv = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const errorDiv = document.getElementById('error');
const gamesContainer = document.getElementById('games-container');

// Set today's date as default
dateInput.value = new Date().toISOString().split('T')[0];

// Event Listeners
loadGamesBtn.addEventListener('click', loadGames);
loadLineupsBtn.addEventListener('click', loadLineups);
loadOddsBtn.addEventListener('click', loadAllOdds);
dateInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        loadGames();
    }
});

// Load games function (gets games from schedule)
async function loadGames() {
    const date = dateInput.value;
    
    if (!date) {
        showError('Por favor selecciona una fecha');
        return;
    }
    
    // Show loading
    loadingText.textContent = 'Cargando juegos...';
    showLoading();
    hideError();
    gamesContainer.innerHTML = '';
    
    try {
        console.log(`Fetching games for date: ${date}`);
        const url = `${API_BASE_URL}/nba/games?date=${date}`;
        console.log(`Request URL: ${url}`);
        
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
        
        console.log(`Response status: ${response.status}`);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch (e) {
                errorData = { message: errorText || `HTTP ${response.status}` };
            }
            throw new Error(errorData.message || `Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
          if (data.success && data.games && data.games.length > 0) {
              displayGames(data.games, false); // false = no lineups loaded yet
          } else {
              showEmptyState('No hay juegos disponibles para esta fecha');
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

// Load lineups function (imports lineups from FantasyNerds)
// Only loads lineups for today (Los Angeles/Tijuana timezone)
async function loadLineups() {
    // Always use today's date in Los Angeles timezone
    const date = getTodayInLATimezone();
    
    console.log(`Loading lineups for today (LA timezone): ${date}`);
    
    // Show loading
    loadingText.textContent = `Cargando lineups desde FantasyNerds para hoy (${date})...`;
    showLoading();
    hideError();
    
    try {
        console.log(`Importing lineups for date: ${date}`);
        const url = `${API_BASE_URL}/nba/lineups/import?date=${date}`;
        console.log(`Request URL: ${url}`);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        // Check if response is ok before parsing JSON
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
        console.log('Import response:', data);
        
        if (data.success) {
            // Reload games with lineups for today
            await loadGamesWithLineups(getTodayInLATimezone());
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

// Load games with lineups (gets games that have lineups)
async function loadGamesWithLineups(date = null) {
    // If no date provided, use the date input value (for manual loading)
    // If date is provided (from loadLineups), use that date
    const queryDate = date || dateInput.value;
    
    if (!queryDate) {
        return;
    }
    
    // Show loading
    loadingText.textContent = 'Cargando juegos con lineups...';
    showLoading();
    hideError();
    gamesContainer.innerHTML = '';
    
    try {
        console.log(`Fetching lineups for date: ${queryDate}`);
        const url = `${API_BASE_URL}/nba/lineups?date=${queryDate}`;
        console.log(`Request URL: ${url}`);
        
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
        console.log('Lineups response:', data);
        // Debug: log lineup_date for each game
        if (data.games) {
            data.games.forEach(game => {
                console.log(`Game ${game.game_id}: game_date=${game.game_date}, lineup_date=${game.lineup_date}`);
            });
        }
        
        if (data.success && data.games && data.games.length > 0) {
            displayGames(data.games, true); // true = lineups loaded
        } else {
            showEmptyState('No hay lineups disponibles para esta fecha');
        }
        
    } catch (error) {
        console.error('Error loading games with lineups:', error);
        showError(`Error al cargar juegos: ${error.message || error}`);
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
}

// Create game card
function createGameCard(game, hasLineups = false) {
    const card = document.createElement('div');
    card.className = 'game-card';
    
    // Use lineup_date if available (for lineups), otherwise use game_date
    // Priority: lineup_date > game_date (lineup_date is the date the lineup was published)
    // If lineups are loaded, prefer lineup_date to show the correct date
    let gameDate;
    if (hasLineups && game.lineup_date) {
        gameDate = game.lineup_date;
    } else {
        gameDate = game.lineup_date || game.game_date || 'N/A';
    }
    const gameTime = game.game_time || 'N/A';
    
    // Debug log
    if (game.lineup_date && game.game_date && game.lineup_date !== game.game_date) {
        console.log(`Date mismatch for game ${game.game_id}: game_date=${game.game_date}, lineup_date=${game.lineup_date}, hasLineups=${hasLineups}, using: ${gameDate}`);
    }
    const hasLineup = hasLineups || game.has_lineup || (game.lineups && Object.keys(game.lineups).length > 0);
    
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
        
        <div class="actions-section">
            ${!hasLineup ? `
                <button class="action-btn" onclick="loadLineupsForGame('${game.game_id}')">
                    Cargar Lineups
                </button>
            ` : ''}
            <button class="odds-btn" onclick="loadOdds('${game.game_id}', this)">
                <span class="btn-text">${hasLineup ? 'Actualizar' : 'Cargar'} Odds de Puntos</span>
                <span class="btn-loading hidden">Cargando...</span>
            </button>
            <div class="odds-container" id="odds-${game.game_id}"></div>
        </div>
        
        <div class="lineups-section">
            <h3>Lineups</h3>
            ${createLineupsHTML(game.lineups || {}, game.away_team, game.away_team_name, game.away_team_logo_url, game.game_id)}
            ${createLineupsHTML(game.lineups || {}, game.home_team, game.home_team_name, game.home_team_logo_url, game.game_id)}
        </div>
    `;
    
    return card;
}

// Load lineups for a specific game
async function loadLineupsForGame(gameId) {
    // Always use today's date in Los Angeles timezone
    const date = getTodayInLATimezone();
    
    loadingText.textContent = `Cargando lineups para hoy (${date})...`;
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/nba/lineups/import?date=${date}`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Reload games with lineups for today
            await loadGamesWithLineups(getTodayInLATimezone());
        } else {
            throw new Error(data.message || 'Error al cargar lineups');
        }
        
    } catch (error) {
        console.error('Error loading lineups for game:', error);
        showError(`Error al cargar lineups: ${error.message || error}`);
    } finally {
        hideLoading();
    }
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
    const positionsHTML = positions.map(position => {
        const player = teamLineup[position];
        if (!player) {
            return `
                <div class="position-card">
                    <div class="position-label">${position}</div>
                    <div class="no-lineup">N/A</div>
                </div>
            `;
        }
        
        const playerStatus = player.player_status || (player.confirmed ? 'STARTER' : 'BENCH');
        const statusBadge = playerStatus === 'STARTER' 
            ? '<span class="status-badge starter">STARTER</span>' 
            : '<span class="status-badge bench">BENCH</span>';
        
        return `
            <div class="position-card" data-player-id="${player.player_id || ''}" data-player-name="${player.player_name}">
                <div class="position-label">${position}</div>
                <img src="${player.player_photo_url || getPlaceholderPlayer()}" 
                     alt="${player.player_name}" 
                     class="player-photo"
                     onerror="this.src='${getPlaceholderPlayer()}'">
                <div class="player-name">${player.player_name}</div>
                <div class="player-id">ID: ${player.player_id || 'N/A'}</div>
                ${statusBadge}
                ${player.confirmed ? '<span class="confirmed-badge">Confirmado</span>' : ''}
                <div class="player-odds" id="odds-${gameId}-${player.player_id || player.player_name}"></div>
            </div>
        `;
    }).join('');
    
    // Get BENCH players (players with position='BENCH' or no position)
    const benchPlayers = [];
    Object.keys(teamLineup).forEach(key => {
        if (key !== 'BENCH' && !positions.includes(key)) {
            // This might be a BENCH player stored with a different key
            const player = teamLineup[key];
            if (player && (player.position === 'BENCH' || player.player_status === 'BENCH')) {
                benchPlayers.push({...player, position: key});
            }
        }
    });
    
    // Also check for BENCH position
    if (teamLineup['BENCH']) {
        if (Array.isArray(teamLineup['BENCH'])) {
            benchPlayers.push(...teamLineup['BENCH'].map(p => ({...p, position: 'BENCH'})));
        } else {
            benchPlayers.push({...teamLineup['BENCH'], position: 'BENCH'});
        }
    }
    
    const benchHTML = benchPlayers.map(player => {
        const statusBadge = '<span class="status-badge bench">BENCH</span>';
        return `
            <div class="position-card bench-card" data-player-id="${player.player_id || ''}" data-player-name="${player.player_name}">
                <div class="position-label">BENCH</div>
                <img src="${player.player_photo_url || getPlaceholderPlayer()}" 
                     alt="${player.player_name}" 
                     class="player-photo"
                     onerror="this.src='${getPlaceholderPlayer()}'">
                <div class="player-name">${player.player_name}</div>
                <div class="player-id">ID: ${player.player_id || 'N/A'}</div>
                ${statusBadge}
                <div class="player-odds" id="odds-${gameId}-${player.player_id || player.player_name}"></div>
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
                ${positionsHTML}
            </div>
            ${benchHTML ? `<div class="bench-players"><h4>Jugadores BENCH (desde Odds)</h4><div class="positions-grid">${benchHTML}</div></div>` : ''}
        </div>
    `;
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

function getPlaceholderPlayer() {
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9IiNkZGQiLz48Y2lyY2xlIGN4PSI0MCIgY3k9IjMwIiByPSIxMCIgZmlsbD0iIzk5OSIvPjxwYXRoIGQ9Ik0yMCA1MHEwIDIwIDIwIDIwaDIwcTIwIDAgMjAgLTIwIiBmaWxsPSIjOTk5Ii8+PC9zdmc+';
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

function showEmptyState(message) {
    gamesContainer.innerHTML = `
        <div class="empty-state">
            <h2>📋 Sin lineups</h2>
            <p>${message}</p>
        </div>
    `;
}

// Load odds for all games of today
async function loadAllOdds() {
    const date = getTodayInLATimezone();
    
    // Show loading
    loadingText.textContent = `Cargando odds para todos los juegos de hoy (${date})...`;
    showLoading();
    hideError();
    
    try {
        // First, get all games for today
        const gamesResponse = await fetch(`${API_BASE_URL}/nba/lineups?date=${date}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!gamesResponse.ok) {
            throw new Error(`Error al obtener juegos: ${gamesResponse.status}`);
        }
        
        const gamesData = await gamesResponse.json();
        
        if (!gamesData.success || !gamesData.games || gamesData.games.length === 0) {
            showError('No hay juegos disponibles para cargar odds');
            return;
        }
        
        // Load odds for each game
        const oddsPromises = gamesData.games.map(game => {
            const buttonElement = document.querySelector(`button[onclick*="loadOdds('${game.game_id}'"]`);
            if (buttonElement && !buttonElement.disabled) {
                return loadOdds(game.game_id, buttonElement).catch(err => {
                    console.error(`Error loading odds for game ${game.game_id}:`, err);
                    return null;
                });
            }
            return Promise.resolve();
        });
        
        await Promise.all(oddsPromises);
        
        showError(''); // Clear any errors
        
    } catch (error) {
        console.error('Error loading all odds:', error);
        showError(`Error al cargar odds: ${error.message || error}`);
    } finally {
        hideLoading();
    }
}

// Load odds for a game
async function loadOdds(gameId, buttonElement) {
    const btnText = buttonElement.querySelector('.btn-text');
    const btnLoading = buttonElement.querySelector('.btn-loading');
    const oddsContainer = document.getElementById(`odds-${gameId}`);
    
    // Check if odds are already loaded (button should be hidden)
    if (buttonElement.style.display === 'none') {
        return; // Already loaded
    }
    
    // Show loading state
    btnText.classList.add('hidden');
    btnLoading.classList.remove('hidden');
    buttonElement.disabled = true;
    oddsContainer.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/nba/games/${gameId}/odds`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.matched_players && data.matched_players.length > 0) {
            displayOdds(gameId, data.matched_players);
            
            // Check if we need to reload games (if no lineups were loaded before)
            const gameCard = buttonElement.closest('.game-card');
            const hasLineup = gameCard && gameCard.querySelector('.lineups-section .team-lineup .positions-grid');
            
            if (!hasLineup) {
                // Reload games to show BENCH players from odds
                await loadGamesWithLineups();
            } else {
                // Just update the odds display
                // Button text changes to "Actualizar" but stays visible
                btnText.textContent = 'Actualizar Odds';
            }
        } else {
            // Show error but keep button visible so user can retry
            oddsContainer.innerHTML = `
                <div class="odds-error">
                    ${data.message || 'No se encontraron odds para este juego'}
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Error loading odds:', error);
        oddsContainer.innerHTML = `
            <div class="odds-error">
                Error al cargar odds: ${error.message}
            </div>
        `;
    } finally {
        // Always restore button state
        btnText.classList.remove('hidden');
        btnLoading.classList.add('hidden');
        buttonElement.disabled = false;
    }
}

// Display odds for matched players
function displayOdds(gameId, matchedPlayers) {
    // Group odds by player (by player_id or player_name if no ID)
    const playerOddsMap = {};
    
    matchedPlayers.forEach(player => {
        // Use player_id if available, otherwise use player_name
        const playerKey = player.player_id || player.player_name;
        if (!playerOddsMap[playerKey]) {
            playerOddsMap[playerKey] = {
                player_name: player.player_name,
                player_id: player.player_id,
                odds: []
            };
        }
        
        // Add odds entry with over/under information
        if (player.points_line) {
            playerOddsMap[playerKey].odds.push({
                points_line: player.points_line,
                over_odds: player.over_odds,
                over_bookmaker: player.over_bookmaker,
                under_odds: player.under_odds,
                under_bookmaker: player.under_bookmaker
            });
        }
    });
    
    // Display odds for each player
    Object.keys(playerOddsMap).forEach(playerKey => {
        // Try both player_id and player_name as selectors
        const playerData = playerOddsMap[playerKey];
        const oddsElementById = playerData.player_id 
            ? document.getElementById(`odds-${gameId}-${playerData.player_id}`)
            : null;
        const oddsElementByName = document.getElementById(`odds-${gameId}-${playerData.player_name}`);
        const oddsElement = oddsElementById || oddsElementByName;
        
        if (oddsElement) {
            oddsElement.innerHTML = createPlayerOddsHTML(playerData);
        }
    });
}

// Create HTML for player odds
function createPlayerOddsHTML(playerData) {
    // Group by points line
    const oddsByLine = {};
    
    playerData.odds.forEach(odd => {
        const key = odd.points_line;
        if (!oddsByLine[key]) {
            oddsByLine[key] = {
                points_line: odd.points_line,
                over_odds: null,
                over_bookmaker: null,
                under_odds: null,
                under_bookmaker: null
            };
        }
        
        // Use the best odds (if multiple lines, keep the first one or best)
        if (odd.over_odds !== null && odd.over_odds !== undefined) {
            oddsByLine[key].over_odds = odd.over_odds;
            oddsByLine[key].over_bookmaker = odd.over_bookmaker;
        }
        if (odd.under_odds !== null && odd.under_odds !== undefined) {
            oddsByLine[key].under_odds = odd.under_odds;
            oddsByLine[key].under_bookmaker = odd.under_bookmaker;
        }
    });
    
    const oddsHTML = Object.values(oddsByLine).map(lineData => {
        // Show both Over and Under if available
        let oddsDisplay = '';
        
        if (lineData.over_odds !== null && lineData.over_odds !== undefined) {
            oddsDisplay += `
                <div class="odds-line-item">
                    <span class="odds-type">Over</span>
                    <span class="odds-value">${formatAmericanOdds(lineData.over_odds)}</span>
                    ${lineData.over_bookmaker ? `<span class="odds-bookmaker">${lineData.over_bookmaker}</span>` : ''}
                </div>
            `;
        }
        
        if (lineData.under_odds !== null && lineData.under_odds !== undefined) {
            oddsDisplay += `
                <div class="odds-line-item">
                    <span class="odds-type">Under</span>
                    <span class="odds-value">${formatAmericanOdds(lineData.under_odds)}</span>
                    ${lineData.under_bookmaker ? `<span class="odds-bookmaker">${lineData.under_bookmaker}</span>` : ''}
                </div>
            `;
        }
        
        if (!oddsDisplay) {
            return '';
        }
        
        return `
            <div class="odds-line">
                <div class="odds-line-header">
                    <span class="odds-points">${lineData.points_line} pts</span>
                </div>
                <div class="odds-line-items">
                    ${oddsDisplay}
                </div>
            </div>
        `;
    }).filter(html => html !== '').join('');
    
    if (!oddsHTML) {
        return '';
    }
    
    return `
        <div class="player-odds-container">
            ${oddsHTML}
        </div>
    `;
}

// Format American odds
function formatAmericanOdds(odds) {
    if (odds > 0) {
        return `+${odds}`;
    }
    return odds.toString();
}


// Load lineups on page load
window.addEventListener('DOMContentLoaded', () => {
    // Optionally auto-load today's lineups
    // loadLineups();
});

