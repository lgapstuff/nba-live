<template>
  <main class="app">
    <section class="app__content" :class="{ 'app__content--playbyplay': playByPlayOpen }">
      <div class="app__main">
        <ScheduleHeader
          :selected-game-id="selectedGameId"
          :loading-game-id="loadingGameId"
          @select="handleGameSelect"
          @loaded="handleScheduleLoaded"
        />
        <LineupPanel
          :game="selectedGame"
          :lineup="lineup"
          :live-stats="liveStats"
          :is-loading="isLineupLoading"
          :error="lineupError"
          :odds-requested="oddsRequested"
          @show-logs="handleShowLogs"
        />
      </div>

      <aside v-if="playByPlayOpen" class="playbyplay-panel">
        <header class="playbyplay-panel__header">
          <div>
            <h3>Play by Play</h3>
            <p class="muted">{{ playByPlayTitle }}</p>
            <p v-if="playByPlayUpdatedLabel" class="muted">Actualizado {{ playByPlayUpdatedLabel }}</p>
          </div>
          <div class="playbyplay-panel__actions">
            <button
              class="playbyplay-refresh"
              type="button"
              :disabled="playByPlayLoading"
              @click="handleLoadPlayByPlay"
            >
              {{ playByPlayLoading ? "..." : "Actualizar" }}
            </button>
            <button class="playbyplay-close" type="button" @click="playByPlayOpen = false">✕</button>
          </div>
        </header>
        <div class="playbyplay-panel__body">
          <div v-if="playByPlayLoading" class="muted">Cargando jugadas...</div>
          <div v-else-if="playByPlayError" class="error">{{ playByPlayError }}</div>
          <div v-else-if="!playByPlayActions.length" class="muted">No hay jugadas disponibles.</div>
          <div v-else class="playbyplay-list">
            <table class="playbyplay-table">
              <thead>
                <tr>
                  <th>Hora</th>
                  <th>Jugada</th>
                  <th>{{ playByPlayTeams.away || "AWAY" }}</th>
                  <th>{{ playByPlayTeams.home || "HOME" }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="action in playByPlayActions" :key="action.orderNumber || action.actionNumber">
                  <td class="playbyplay-time">
                    {{ formatPlayPeriod(action.period) }} {{ formatPlayClock(action.clock) }}
                  </td>
                  <td class="playbyplay-desc">
                    <span v-if="action.teamTricode" class="playbyplay-team">{{ action.teamTricode }}</span>
                    <span>{{ action.description || action.actionType || "--" }}</span>
                  </td>
                  <td class="playbyplay-score">{{ action.scoreAway ?? "--" }}</td>
                  <td class="playbyplay-score">{{ action.scoreHome ?? "--" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </aside>
    </section>
    <button
      class="odds-fab"
      type="button"
      :disabled="isOddsLoading"
      @click="handleLoadOdds"
      aria-label="Cargar odds"
      title="Cargar O/U"
    >
      {{ isOddsLoading ? "..." : "$" }}
    </button>
    <button
      class="playbyplay-fab"
      type="button"
      :disabled="playByPlayLoading"
      @click="handleLoadPlayByPlay"
      aria-label="Ver play by play"
      title="Play by Play"
    >
      {{ playByPlayLoading ? "..." : "PBP" }}
    </button>
    <button
      class="value-fab"
      type="button"
      @click="handleMostValueClick"
      aria-label="Listar mayores valores"
      title="Listar mayores valores"
    >
      +
    </button>
    <button
      class="all-odds-fab"
      type="button"
      @click="handleLoadAllOdds"
      aria-label="Cargar odds de todos los eventos"
      title="Cargar odds de todos los eventos"
    >
      ALL
    </button>
  </main>
</template>

<script setup>
import ScheduleHeader from "./components/ScheduleHeader.vue";
import LineupPanel from "./components/LineupPanel.vue";
import { computed, onMounted, ref } from "vue";
import { fetchLineupsByDate, fetchLineupByTeams, fetchGameOdds, loadGameLogsForEvent, fetchPlayerGameLogs, loadPlayerGameLogs, fetchCdnBoxscore, fetchCdnPlayByPlay } from "./api/endpoints";

const LINEUPS_CACHE_KEY = "livenba_lineups_cache";
const readLineupsCache = () => {
  try {
    const stored = localStorage.getItem(LINEUPS_CACHE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
};
const persistLineupsCache = (cache) => {
  try {
    localStorage.setItem(LINEUPS_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // ignore storage errors
  }
};

const selectedGame = ref(null);
const selectedGameId = ref("");
const lineup = ref(null);
const isLineupLoading = ref(false);
const lineupError = ref("");
const resolvedGameId = ref("");
const isOddsLoading = ref(false);
const oddsError = ref("");
const oddsRequested = ref(false);
const liveStats = ref({});
const lineupsCache = ref(readLineupsCache());
const scheduleGames = ref([]);
const loadingGameId = ref("");
const playByPlayOpen = ref(false);
const playByPlayLoading = ref(false);
const playByPlayError = ref("");
const playByPlay = ref(null);
const playByPlayUpdatedAt = ref(null);

const getTodayInLATimezone = () => {
  const now = new Date();
  const laTime = new Date(now.toLocaleString("en-US", { timeZone: "America/Los_Angeles" }));
  const year = laTime.getFullYear();
  const month = String(laTime.getMonth() + 1).padStart(2, "0");
  const day = String(laTime.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const formatDateKey = (value) => {
  if (!value) {
    return "";
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const laDate = new Date(date.toLocaleString("en-US", { timeZone: "America/Los_Angeles" }));
  const year = laDate.getFullYear();
  const month = String(laDate.getMonth() + 1).padStart(2, "0");
  const day = String(laDate.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const resolveGameDate = (game) => {
  const rawDate = game?.gameDate;
  if (rawDate) {
    if (/^\d{4}-\d{2}-\d{2}$/.test(rawDate)) {
      return rawDate;
    }
    if (/^\d{8}$/.test(rawDate)) {
      return `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}`;
    }
    const normalized = formatDateKey(rawDate);
    if (normalized) {
      return normalized;
    }
  }
  const fromTime = formatDateKey(game?.gameTimeUTC || game?.gameEt);
  if (fromTime) {
    return fromTime;
  }
  return getTodayInLATimezone();
};

const getDateCandidates = (game) => {
  const candidates = [];
  const resolved = resolveGameDate(game);
  if (resolved) {
    candidates.push(resolved);
  }
  const fromTime = formatDateKey(game?.gameTimeUTC || game?.gameEt);
  if (fromTime) {
    candidates.push(fromTime);
  }
  const today = getTodayInLATimezone();
  if (today) {
    candidates.push(today);
  }
  if (today) {
    const date = new Date(`${today}T00:00:00`);
    if (!Number.isNaN(date.getTime())) {
      date.setDate(date.getDate() - 1);
      const prev = formatDateKey(date);
      if (prev) {
        candidates.push(prev);
      }
    }
  }
  return Array.from(new Set(candidates.filter(Boolean)));
};

const shouldFetchBoxscore = (game) => {
  const status = Number(game?.gameStatus);
  if (!Number.isNaN(status)) {
    return status > 1;
  }
  return Boolean(game?.gameClock);
};

const preloadLineupsForDate = async (date) => {
  if (!date || lineupsCache.value[date]) {
    return;
  }
  const data = await fetchLineupsByDate(date);
  if (data?.success && Array.isArray(data.games)) {
    lineupsCache.value[date] = data.games;
    persistLineupsCache(lineupsCache.value);
  }
};

const handleGameSelect = async (game) => {
  selectedGame.value = game;
  selectedGameId.value = game.gameId;
  lineup.value = null;
  resolvedGameId.value = "";
  lineupError.value = "";
  oddsRequested.value = false;
  liveStats.value = {};
  playByPlayOpen.value = false;
  playByPlayError.value = "";
  playByPlay.value = null;
  playByPlayUpdatedAt.value = null;
  isLineupLoading.value = true;
  try {
    const candidates = getDateCandidates(game);
    let cachedLineups = [];
    let resolvedDate = "";
    for (const candidate of candidates) {
      await preloadLineupsForDate(candidate);
      const candidateLineups = lineupsCache.value[candidate] || [];
      if (candidateLineups.length) {
        cachedLineups = candidateLineups;
        resolvedDate = candidate;
        break;
      }
    }
    let match = cachedLineups.length
      ? findLineupForTeams(cachedLineups, game.homeTricode, game.awayTricode)
      : null;
    if (!match?.lineups) {
      const fallbackDate = resolveGameDate(game);
      const resolved = await fetchLineupByTeams(game.homeTricode, game.awayTricode, fallbackDate);
      if (resolved?.lineup?.lineups) {
        match = resolved.lineup;
        if (fallbackDate) {
          const cache = lineupsCache.value[fallbackDate] || [];
          const exists = cache.some((item) => String(item.game_id) === String(match.game_id));
          if (!exists) {
            cache.push(match);
            lineupsCache.value[fallbackDate] = cache;
            persistLineupsCache(lineupsCache.value);
          }
        }
      }
    }
    if (!match?.lineups) {
      lineupError.value = cachedLineups.length
        ? "No se encontró lineup para ese juego."
        : "No se pudo resolver la fecha del juego.";
      return;
    }
    resolvedGameId.value = match.game_id || "";
    lineup.value = match;
    if (resolvedGameId.value) {
      loadGameLogsForEvent(resolvedGameId.value).catch(() => undefined);
    }
    if (game?.gameId && shouldFetchBoxscore(game)) {
      const boxscore = await fetchCdnBoxscore(game.gameId);
      if (boxscore?.boxscore?.game?.homeTeam || boxscore?.boxscore?.game?.awayTeam) {
        const gameData = boxscore.boxscore.game;
        const home = gameData.homeTeam || {};
        const away = gameData.awayTeam || {};
        selectedGame.value = {
          ...selectedGame.value,
          homeScore: home.score ?? selectedGame.value.homeScore,
          awayScore: away.score ?? selectedGame.value.awayScore,
          gameClock: gameData.gameClock || selectedGame.value.gameClock,
          gamePeriod: gameData.period ?? selectedGame.value.gamePeriod,
          gameStatusText: gameData.gameStatusText || selectedGame.value.gameStatusText,
          gameStatus: gameData.gameStatus ?? selectedGame.value.gameStatus
        };

        liveStats.value = buildLiveStatsMap(
          home.players || [],
          away.players || [],
          home.teamTricode || gameData.homeTeam?.teamTricode,
          away.teamTricode || gameData.awayTeam?.teamTricode
        );
      }
    }
  } catch (err) {
    lineupError.value = err?.message || "Error inesperado al cargar el lineup.";
  } finally {
    isLineupLoading.value = false;
  }
};

const handleScheduleLoaded = (games) => {
  scheduleGames.value = Array.isArray(games) ? games : [];
};

const handleLoadOdds = async () => {
  oddsError.value = "";
  const gameId = resolvedGameId.value || lineup.value?.game_id;
  if (!gameId) {
    oddsError.value = "Selecciona un juego con lineup antes de cargar O/U.";
    return;
  }
  isOddsLoading.value = true;
  try {
    const data = await fetchGameOdds(gameId);
    if (!data?.success) {
      oddsError.value = data?.message || "No se pudieron cargar los odds.";
      return;
    }
    oddsRequested.value = true;
    if (lineup.value && Array.isArray(data?.matched_players)) {
      const { lineup: updatedLineup, updatedPlayerIds } = applyOddsToLineup(lineup.value, data.matched_players);
      lineup.value = updatedLineup;
      const gameDate = updatedLineup?.lineup_date || updatedLineup?.game_date;
      const cached = gameDate ? lineupsCache.value[gameDate] : null;
      if (gameDate && Array.isArray(cached)) {
        const idx = cached.findIndex((item) => String(item.game_id) === String(updatedLineup.game_id));
        if (idx !== -1) {
          cached[idx] = updatedLineup;
          persistLineupsCache(lineupsCache.value);
        }
      }
      if (updatedPlayerIds.length) {
        setTimeout(() => {
          clearOddsFlash(lineup.value, updatedPlayerIds);
        }, 3500);
      }
    }
    if (selectedGame.value?.gameId && shouldFetchBoxscore(selectedGame.value)) {
      const boxscore = await fetchCdnBoxscore(selectedGame.value.gameId);
      if (boxscore?.boxscore?.game?.homeTeam || boxscore?.boxscore?.game?.awayTeam) {
        const gameData = boxscore.boxscore.game;
        const home = gameData.homeTeam || {};
        const away = gameData.awayTeam || {};
        selectedGame.value = {
          ...selectedGame.value,
          homeScore: home.score ?? selectedGame.value.homeScore,
          awayScore: away.score ?? selectedGame.value.awayScore,
          gameClock: gameData.gameClock || selectedGame.value.gameClock,
          gamePeriod: gameData.period ?? selectedGame.value.gamePeriod,
          gameStatusText: gameData.gameStatusText || selectedGame.value.gameStatusText,
          gameStatus: gameData.gameStatus ?? selectedGame.value.gameStatus
        };

        liveStats.value = buildLiveStatsMap(
          home.players || [],
          away.players || [],
          home.teamTricode || gameData.homeTeam?.teamTricode,
          away.teamTricode || gameData.awayTeam?.teamTricode
        );
      }
    }
    // No need to refresh lineup here; odds already return player lines.
  } catch (err) {
    oddsError.value = err?.message || "Error inesperado al cargar los odds.";
  } finally {
    isOddsLoading.value = false;
  }
};

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const handleLoadAllOdds = async () => {
  if (!scheduleGames.value.length) {
    return;
  }
  for (const game of scheduleGames.value) {
    const statusText = String(game?.gameStatusText || "").toLowerCase();
    if (Number(game?.gameStatus) === 3 || statusText.includes("final")) {
      continue;
    }
    loadingGameId.value = game.gameId;
    try {
      const gameDate = resolveGameDate(game);
      await preloadLineupsForDate(gameDate);
      const cachedLineups = lineupsCache.value[gameDate] || [];
      const match = findLineupForTeams(cachedLineups, game.homeTricode, game.awayTricode);
      if (!match?.game_id) {
        await wait(1000);
        continue;
      }
      const data = await fetchGameOdds(match.game_id);
      if (data?.success && lineup.value && Array.isArray(data?.matched_players)) {
        const { lineup: updatedLineup, updatedPlayerIds } = applyOddsToLineup(lineup.value, data.matched_players);
        lineup.value = updatedLineup;
        oddsRequested.value = true;
        const cached = gameDate ? lineupsCache.value[gameDate] : null;
        if (gameDate && Array.isArray(cached)) {
          const idx = cached.findIndex((item) => String(item.game_id) === String(updatedLineup.game_id));
          if (idx !== -1) {
            cached[idx] = updatedLineup;
            persistLineupsCache(lineupsCache.value);
          }
        }
        if (updatedPlayerIds.length) {
          setTimeout(() => {
            clearOddsFlash(lineup.value, updatedPlayerIds);
          }, 3500);
        }
      }
    } catch {
      // ignore individual odds errors
    }
    await wait(1000);
  }
  loadingGameId.value = "";
};

const handleLoadPlayByPlay = async () => {
  playByPlayError.value = "";
  const gameId = selectedGame.value?.gameId || resolvedGameId.value || lineup.value?.game_id;
  playByPlayOpen.value = true;
  if (!gameId) {
    playByPlayError.value = "Selecciona un juego antes de cargar el play by play.";
    return;
  }
  playByPlayLoading.value = true;
  try {
    const data = await fetchCdnPlayByPlay(gameId);
    if (!data?.success) {
      playByPlayError.value = data?.error || "No se pudo cargar el play by play.";
      return;
    }
    playByPlay.value = data.playbyplay || data.playByPlay || data;
    playByPlayUpdatedAt.value = new Date();
  } catch (err) {
    playByPlayError.value = err?.message || "Error inesperado al cargar el play by play.";
  } finally {
    playByPlayLoading.value = false;
  }
};

const playByPlayTeams = computed(() => {
  const home = selectedGame.value?.homeTricode
    || selectedGame.value?.homeTeam?.teamTricode
    || selectedGame.value?.homeTeamTricode
    || "";
  const away = selectedGame.value?.awayTricode
    || selectedGame.value?.awayTeam?.teamTricode
    || selectedGame.value?.awayTeamTricode
    || "";
  return { home, away };
});

const playByPlayTitle = computed(() => {
  if (!playByPlayOpen.value) {
    return "";
  }
  const { home, away } = playByPlayTeams.value;
  if (!home && !away) {
    return "";
  }
  return `${away || "AWAY"} vs ${home || "HOME"}`;
});

const playByPlayUpdatedLabel = computed(() => {
  if (!playByPlayUpdatedAt.value) {
    return "";
  }
  return playByPlayUpdatedAt.value.toLocaleTimeString("es-MX", {
    hour: "2-digit",
    minute: "2-digit"
  });
});

const playByPlayActions = computed(() => {
  const actions = playByPlay.value?.game?.actions || playByPlay.value?.actions || [];
  if (!Array.isArray(actions)) {
    return [];
  }
  return [...actions].sort((a, b) => (b.orderNumber || 0) - (a.orderNumber || 0));
});

const formatPlayClock = (clock) => {
  if (!clock) {
    return "--:--";
  }
  const match = /PT(\d+)M(\d+)\.(\d+)S/.exec(clock);
  if (!match) {
    return String(clock);
  }
  const minutes = String(match[1]).padStart(2, "0");
  const seconds = String(match[2]).padStart(2, "0");
  return `${minutes}:${seconds}`;
};

const formatPlayPeriod = (period) => {
  if (!period) {
    return "Q?";
  }
  return `Q${period}`;
};

const handleMostValueClick = () => {
  window.location.assign("/most-value");
};

const normalizeName = (value) => {
  if (!value) {
    return "";
  }
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z\s]/g, "")
    .toLowerCase()
    .trim();
};

const getBoxscorePlayerName = (player) => {
  if (player?.firstName || player?.lastName) {
    return `${player?.firstName || ""} ${player?.lastName || ""}`.trim();
  }
  return player?.name || "";
};

const normalizeTeamTricode = (team) => {
  const normalized = String(team || "").trim().toUpperCase();
  const map = {
    NO: "NOP",
    NY: "NYK",
    GS: "GSW",
    PHO: "PHX",
    SA: "SAS"
  };
  return map[normalized] || normalized;
};

const findLineupForTeams = (games, homeTeam, awayTeam) => {
  const homeKey = normalizeTeamTricode(homeTeam);
  const awayKey = normalizeTeamTricode(awayTeam);
  return games.find((game) => {
    const home = normalizeTeamTricode(game?.home_team);
    const away = normalizeTeamTricode(game?.away_team);
    return (home === homeKey && away === awayKey) || (home === awayKey && away === homeKey);
  }) || null;
};

const buildTeamStatsIndex = (players) => {
  const byId = {};
  const byName = {};
  players.forEach((player) => {
    const statsSource = player?.statistics || {};
    const stats = {
      pts: statsSource.points ?? player.points ?? null,
      ast: statsSource.assists ?? player.assists ?? null,
      reb: statsSource.reboundsTotal ?? statsSource.rebounds ?? player.rebounds ?? null,
      pf: statsSource.foulsPersonal ?? statsSource.fouls ?? player.fouls ?? null,
      min: statsSource.minutesCalculated ?? statsSource.minutes ?? player.min ?? null,
      status: player.status || "",
      oncourt: player.oncourt ?? player.onCourt ?? "",
      played: player.played ?? ""
    };
    if (player?.personId) {
      byId[player.personId] = stats;
    }
    const fullName = getBoxscorePlayerName(player);
    const key = normalizeName(fullName);
    if (key) {
      byName[key] = stats;
    }
  });
  return { byId, byName };
};

const buildLiveStatsMap = (homePlayers, awayPlayers, homeTeamTricode = "", awayTeamTricode = "") => {
  const byTeam = {};
  const homeKey = normalizeTeamTricode(homeTeamTricode);
  const awayKey = normalizeTeamTricode(awayTeamTricode);
  if (homeKey) {
    byTeam[homeKey] = buildTeamStatsIndex(homePlayers);
  }
  if (awayKey) {
    byTeam[awayKey] = buildTeamStatsIndex(awayPlayers);
  }
  const merged = buildTeamStatsIndex([...homePlayers, ...awayPlayers]);
  return {
    byTeam,
    byId: merged.byId,
    byName: merged.byName
  };
};

const applyOddsToLineup = (lineupData, matchedPlayers) => {
  if (!lineupData?.lineups || !Array.isArray(matchedPlayers) || matchedPlayers.length === 0) {
    return { lineup: lineupData, updatedPlayerIds: [] };
  }
  const updated = JSON.parse(JSON.stringify(lineupData));
  const updatedPlayerIds = new Set();
  const teamKeys = Object.keys(updated.lineups || {});
  const teamMap = teamKeys.reduce((acc, key) => {
    acc[normalizeTeamTricode(key)] = key;
    return acc;
  }, {});

  const updatePlayerData = (target, source) => {
    const nextPoints = source.points_line ?? target.points_line ?? null;
    const nextAssists = source.assists_line ?? target.assists_line ?? null;
    const nextRebounds = source.rebounds_line ?? target.rebounds_line ?? null;
    const hasChanged = (
      nextPoints !== (target.points_line ?? null)
      || nextAssists !== (target.assists_line ?? null)
      || nextRebounds !== (target.rebounds_line ?? null)
    );

    target.points_line = nextPoints;
    target.assists_line = nextAssists;
    target.rebounds_line = nextRebounds;
    if (source.over_under_history) {
      target.over_under_history = source.over_under_history;
    }
    if (hasChanged && source.player_id) {
      updatedPlayerIds.add(String(source.player_id));
      target.oddsFlash = true;
    }
  };

  matchedPlayers.forEach((player) => {
    const teamKey = teamMap[normalizeTeamTricode(player.team)] || null;
    if (!teamKey) {
      return;
    }
    const teamLineups = updated.lineups[teamKey];
    let matched = false;

    ["PG", "SG", "SF", "PF", "C"].forEach((position) => {
      const current = teamLineups[position];
      if (!current || matched) {
        return;
      }
      const idMatch = String(current.player_id) === String(player.player_id);
      const nameMatch = normalizeName(current.player_name) === normalizeName(player.player_name);
      if (idMatch || nameMatch) {
        updatePlayerData(current, player);
        matched = true;
      }
    });

    if (matched) {
      return;
    }

    if (!Array.isArray(teamLineups.BENCH)) {
      teamLineups.BENCH = [];
    }
    const benchMatch = teamLineups.BENCH.find((current) => {
      const idMatch = String(current.player_id) === String(player.player_id);
      const nameMatch = normalizeName(current.player_name) === normalizeName(player.player_name);
      return idMatch || nameMatch;
    });

    if (benchMatch) {
      updatePlayerData(benchMatch, player);
      return;
    }

    teamLineups.BENCH.push({
      player_id: player.player_id,
      player_name: player.player_name,
      player_photo_url: null,
      confirmed: false,
      player_status: "BENCH",
      points_line: player.points_line ?? null,
      assists_line: player.assists_line ?? null,
      rebounds_line: player.rebounds_line ?? null,
      over_under_history: player.over_under_history,
      oddsFlash: true
    });
    if (player.player_id) {
      updatedPlayerIds.add(String(player.player_id));
    }
  });

  return { lineup: updated, updatedPlayerIds: Array.from(updatedPlayerIds) };
};

const clearOddsFlash = (lineupData, playerIds) => {
  if (!lineupData?.lineups || !Array.isArray(playerIds) || playerIds.length === 0) {
    return;
  }
  const ids = new Set(playerIds.map((id) => String(id)));
  Object.values(lineupData.lineups).forEach((teamLineup) => {
    ["PG", "SG", "SF", "PF", "C"].forEach((position) => {
      const player = teamLineup?.[position];
      if (player && ids.has(String(player.player_id))) {
        player.oddsFlash = false;
      }
    });
    if (Array.isArray(teamLineup?.BENCH)) {
      teamLineup.BENCH.forEach((player) => {
        if (player && ids.has(String(player.player_id))) {
          player.oddsFlash = false;
        }
      });
    }
  });
};

onMounted(() => {
  const today = getTodayInLATimezone();
  preloadLineupsForDate(today).catch(() => undefined);
});

const handleShowLogs = async (player) => {
  if (!player?.playerId) {
    return;
  }
  const popup = openLogsWindow(player?.name || "Game Logs");
  renderLoading(popup);
  try {
    const withTimeout = (promise, timeoutMs) => Promise.race([
      promise,
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Tiempo de espera agotado")), timeoutMs);
      })
    ]);

    let data = await fetchPlayerGameLogs(player.playerId);
    if (data?.success && Array.isArray(data.game_logs) && data.game_logs.length === 0) {
      const loadResult = await withTimeout(
        loadPlayerGameLogs(player.playerId, player.name),
        20000
      );
      if (!loadResult?.success) {
        renderError(popup, loadResult?.message || "No se pudieron cargar los game logs desde NBA API.");
        return;
      }
      data = await fetchPlayerGameLogs(player.playerId);
    }
    if (!data?.success) {
      renderError(popup, data?.message || "No se pudieron cargar los game logs.");
      return;
    }
    renderLogs(popup, player, data.game_logs || []);
  } catch (err) {
    renderError(popup, err?.message || "Error inesperado al cargar los game logs.");
  }
};

const openLogsWindow = (title) => {
  const width = 980;
  const height = 720;
  const left = window.screenX + (window.outerWidth - width) / 2;
  const top = window.screenY + (window.outerHeight - height) / 2;
  const popup = window.open(
    "",
    "_blank",
    `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
  );
  if (popup) {
    popup.document.title = title;
  }
  return popup;
};

const escapeHtml = (value) => {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
};

const formatDate = (value) => {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
};

const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return Number(value).toFixed(1);
};

const renderLoading = (popup) => {
  if (!popup) {
    return;
  }
  popup.document.body.innerHTML = `
    <div style="font-family: 'Segoe UI', sans-serif; padding: 24px;">
      <h2>Cargando game logs...</h2>
    </div>
  `;
};

const renderError = (popup, message) => {
  if (!popup) {
    return;
  }
  popup.document.body.innerHTML = `
    <div style="font-family: 'Segoe UI', sans-serif; padding: 24px; color: #b91c1c;">
      <h2>Error</h2>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
};

const renderLogs = (popup, player, logs) => {
  if (!popup) {
    return;
  }
  const safeLogs = Array.isArray(logs) ? logs : [];
  const stats = [
    { key: "points", label: "Puntos", lineKey: "pointsLine" },
    { key: "assists", label: "Asistencias", lineKey: "assistsLine" },
    { key: "rebounds", label: "Rebotes", lineKey: "reboundsLine" }
  ];
  const defaultStat = "points";

  const getStatProbability = (history, type) => {
    if (!history || !history.total_games) {
      return null;
    }
    const total = Number(history.total_games || 0);
    if (!total) {
      return null;
    }
    let over = 0;
    let under = 0;
    if (type === "points") {
      over = Number(history.over_count || 0);
      under = Number(history.under_count || 0);
    } else if (type === "assists") {
      over = Number(history.assists_over_count || 0);
      under = Number(history.assists_under_count || 0);
    } else if (type === "rebounds") {
      over = Number(history.rebounds_over_count || 0);
      under = Number(history.rebounds_under_count || 0);
    }
    if (!over && !under) {
      return null;
    }
    const best = Math.max(over, under);
    const percent = (best / total) * 100;
    const side = over >= under ? "OVER" : "UNDER";
    return { percent, side, type };
  };

  const getTabClass = (stat) => {
    const prob = getStatProbability(player?.over_under_history, stat.key);
    if (!prob) {
      return "";
    }
    if (prob.percent >= 80) {
      return "stat-tab--red";
    }
    if (prob.percent >= 70) {
      return "stat-tab--platinum";
    }
    if (prob.percent >= 60) {
      return "stat-tab--green";
    }
    if (prob.percent >= 50) {
      return "stat-tab--yellow";
    }
    return "";
  };

  const getLine = (stat) => {
    const rawLine = stat?.lineKey ? player?.[stat.lineKey] : null;
    if (rawLine === null || rawLine === undefined || Number.isNaN(rawLine)) {
      return "";
    }
    return Number(rawLine).toFixed(1);
  };

  const getOutcome = (value, line) => {
    if (line === null || line === undefined || Number.isNaN(line)) {
      return "--";
    }
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "--";
    }
    return Number(value) > Number(line) ? "OVER" : "UNDER";
  };

  const buildSummary = (stat) => {
    if (!safeLogs.length) {
      return { total: 0, over: 0, under: 0, average: null };
    }
    let total = 0;
    let over = 0;
    let under = 0;
    let sum = 0;
    const line = Number(getLine(stat));
    safeLogs.forEach((log) => {
      const value = Number(log?.[stat.key]);
      if (Number.isNaN(value)) {
        return;
      }
      total += 1;
      sum += value;
      if (!Number.isNaN(line)) {
        if (value > line) {
          over += 1;
        } else {
          under += 1;
        }
      }
    });
    const average = total ? sum / total : null;
    return { total, over, under, average };
  };

  const buildRows = (stat) => safeLogs
    .map((log) => {
      const line = Number(getLine(stat));
      const value = log?.[stat.key];
      const outcome = getOutcome(value, line);
      const rowClass = outcome === "OVER" ? "row-over" : outcome === "UNDER" ? "row-under" : "";
      return `
        <tr class="${rowClass}">
          <td>${escapeHtml(formatDate(log.game_date))}</td>
          <td>${escapeHtml(formatNumber(log.minutes_played))}</td>
          <td>${escapeHtml(formatNumber(value))}</td>
          <td>${escapeHtml(log.start_position || log.starter_status || "--")}</td>
          <td>${escapeHtml(getLine(stat) || "--")}</td>
          <td><span class="pill">${outcome}</span></td>
        </tr>
      `;
    })
    .join("");

  const panels = stats
    .map((stat) => {
      const isActive = stat.key === defaultStat;
      const line = getLine(stat);
      const summary = buildSummary(stat);
      const rows = buildRows(stat);
      return `
        <div class="stat-panel ${isActive ? "active" : ""}" data-stat="${stat.key}">
          <div class="stat-summary">
            <span>Total: <strong>${summary.total}</strong></span>
            <span>Promedio: <strong>${escapeHtml(formatNumber(summary.average))}</strong></span>
            <span>OVER: <strong class="text-over">${summary.over}</strong></span>
            <span>UNDER: <strong class="text-under">${summary.under}</strong></span>
            <span>Linea: <strong>${escapeHtml(line || "--")}</strong></span>
          </div>
          <table class="logs-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>MIN</th>
                <th>${escapeHtml(stat.label)}</th>
                <th>ROL</th>
                <th>Linea</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              ${rows || "<tr><td colspan='6'>No hay datos.</td></tr>"}
            </tbody>
          </table>
        </div>
      `;
    })
    .join("");

  popup.document.body.innerHTML = `
    <style>
      body { margin: 0; font-family: 'Segoe UI', sans-serif; background: #f8fafc; }
      .container { padding: 20px 24px 32px; }
      h2 { margin: 0 0 4px; }
      .stat-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 16px; }
      .stat-tab { border: 1px solid #e2e8f0; background: #fff; color: #334155; padding: 6px 12px; border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer; }
      .stat-tab.active { border-color: #4f46e5; background: #eef2ff; color: #4338ca; }
      .stat-tab--red { border-color: #ef4444; background: #fee2e2; color: #991b1b; }
      .stat-tab--platinum { border-color: #a855f7; background: #f3e8ff; color: #6b21a8; }
      .stat-tab--green { border-color: #22c55e; background: #dcfce7; color: #166534; }
      .stat-tab--yellow { border-color: #f59e0b; background: #fef3c7; color: #92400e; }
      .stat-summary { display: flex; gap: 16px; flex-wrap: wrap; color: #475569; font-size: 13px; margin-bottom: 12px; }
      .text-over { color: #1d4ed8; }
      .text-under { color: #b91c1c; }
      .stat-panel { display: none; }
      .stat-panel.active { display: block; }
      .logs-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 12px 24px rgba(15, 23, 42, 0.1); }
      .logs-table th, .logs-table td { padding: 10px 12px; font-size: 13px; text-align: left; border-bottom: 1px solid #e2e8f0; }
      .logs-table th { background: #6366f1; color: #fff; text-transform: uppercase; font-size: 11px; letter-spacing: .04em; }
      .logs-table tr:last-child td { border-bottom: none; }
      .pill { display: inline-block; padding: 4px 10px; border-radius: 999px; font-weight: 700; font-size: 11px; background: #e2e8f0; color: #475569; }
      .row-over { background: #ecfdf3; }
      .row-over .pill { background: #22c55e; color: #fff; box-shadow: 0 8px 16px rgba(34, 197, 94, 0.2); }
      .row-under { background: #fff1f2; }
      .row-under .pill { background: #ef4444; color: #fff; box-shadow: 0 8px 16px rgba(239, 68, 68, 0.2); }
    </style>
    <div class="container">
      <h2>${escapeHtml(player?.name || "Game Logs")}</h2>
      <div class="stat-tabs">
        ${stats.map((stat) => {
          const isActive = stat.key === defaultStat;
          const tabClass = getTabClass(stat);
          const classes = ["stat-tab", tabClass, isActive ? "active" : ""].filter(Boolean).join(" ");
          return `<button class="${classes}" data-stat="${stat.key}">${escapeHtml(stat.label)}</button>`;
        }).join("")}
      </div>
      ${panels}
    </div>
  `;

  const tabs = Array.from(popup.document.querySelectorAll(".stat-tab"));
  const panelNodes = Array.from(popup.document.querySelectorAll(".stat-panel"));
  const setActive = (stat) => {
    tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.stat === stat));
    panelNodes.forEach((panel) => panel.classList.toggle("active", panel.dataset.stat === stat));
  };
  tabs.forEach((tab) => tab.addEventListener("click", () => setActive(tab.dataset.stat)));
};
</script>

<style scoped>
.app {
  width: 100%;
  margin: 0;
  padding: 0 12px 80px;
}

.app__content {
  display: grid;
  gap: 16px;
  margin-top: 0;
}

.app__content--playbyplay {
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  align-items: start;
}

.app__main {
  display: grid;
  gap: 16px;
}

.playbyplay-panel {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.12);
  padding: 12px 14px;
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.playbyplay-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.playbyplay-panel__header h3 {
  margin: 0 0 4px;
}

.playbyplay-panel__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.playbyplay-refresh {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.playbyplay-refresh:disabled {
  opacity: 0.7;
  cursor: wait;
}

.playbyplay-close {
  border: none;
  background: #f1f5f9;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
}

.playbyplay-panel__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 120px;
}

.playbyplay-list {
  flex: 1;
  overflow-y: auto;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.playbyplay-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.playbyplay-table th,
.playbyplay-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
}

.playbyplay-table th {
  position: sticky;
  top: 0;
  background: #0f172a;
  color: #fff;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.playbyplay-time {
  white-space: nowrap;
  font-weight: 700;
  color: #0f172a;
}

.playbyplay-desc {
  color: #0f172a;
}

.playbyplay-team {
  display: inline-block;
  font-weight: 700;
  color: #1d4ed8;
  margin-right: 6px;
}

.playbyplay-score {
  text-align: right;
  font-weight: 700;
  color: #0f172a;
}

.odds-fab {
  position: fixed;
  right: 20px;
  bottom: 24px;
  width: 62px;
  height: 62px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: #ffffff;
  font-weight: 800;
  font-size: 20px;
  box-shadow: 0 14px 24px rgba(79, 70, 229, 0.35);
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.7);
}

.odds-fab:disabled {
  opacity: 0.7;
  cursor: wait;
}

.playbyplay-fab {
  position: fixed;
  right: 20px;
  bottom: 98px;
  width: 62px;
  height: 62px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
  color: #ffffff;
  font-weight: 800;
  font-size: 12px;
  letter-spacing: 0.06em;
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.35);
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.7);
}

.playbyplay-fab:disabled {
  opacity: 0.7;
  cursor: wait;
}

.value-fab {
  position: fixed;
  left: 20px;
  bottom: 24px;
  width: 62px;
  height: 62px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
  color: #ffffff;
  font-weight: 800;
  font-size: 20px;
  box-shadow: 0 14px 24px rgba(37, 99, 235, 0.35);
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.7);
}

.all-odds-fab {
  position: fixed;
  left: 20px;
  bottom: 98px;
  width: 62px;
  height: 62px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #0f172a 0%, #1f2937 100%);
  color: #ffffff;
  font-weight: 800;
  font-size: 12px;
  letter-spacing: 0.06em;
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.35);
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.7);
}
</style>
