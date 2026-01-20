<template>
  <main class="app">
    <section class="app__content" :class="activeMainTab === 'live-follow' ? 'app__content--playbyplay' : 'app__content--single'">
      <div class="app__main">
        <nav class="top-nav" aria-label="Primary">
          <button
            type="button"
            class="top-nav__item"
            :class="{ 'top-nav__item--active': activeMainTab === 'games' }"
            @click="activeMainTab = 'games'"
          >
            Games
          </button>
          <button
            type="button"
            class="top-nav__item"
            :class="{ 'top-nav__item--active': activeMainTab === 'live-follow' }"
            @click="activeMainTab = 'live-follow'"
          >
            Live Follow
          </button>
        </nav>
        <div v-show="activeMainTab === 'games'">
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
            :subs-stats="playByPlaySubs"
            :minutes-avg="minutesAvgByPlayer"
            :is-loading="isLineupLoading"
            :error="lineupError"
            :odds-requested="oddsRequested"
            :timeout-label="timeoutLabel"
            :followed-players="followedPlayers"
            @show-logs="handleShowLogs"
            @follow-request="handleFollowRequest"
          />
        </div>
        <section v-show="activeMainTab === 'live-follow'" class="live-follow">
          <div v-if="!liveFollowGroups.length" class="muted live-follow__empty">
            No hay jugadores seguidos en juegos en vivo.
          </div>
          <div v-for="group in liveFollowGroups" :key="group.gameId" class="live-follow__game">
            <div class="live-follow__card" @click="selectedLiveFollowGameId = group.gameId">
              <div class="live-follow__row live-follow__row--header">
                <div class="live-follow__title">
                  <span class="live-follow__clock">{{ group.timeLabel }}</span>
                  <span class="live-follow__teams">{{ group.matchup }}</span>
                </div>
                <span v-if="group.scoreLabel" class="live-follow__score">{{ group.scoreLabel }}</span>
                <span class="live-follow__spacer" aria-hidden="true"></span>
              </div>
              <div class="live-follow__rows">
                <div v-for="item in group.items" :key="item.key" class="live-follow__row">
                  <span class="playbyplay-followed__name">
                    <span
                      class="playbyplay-followed__live-dot"
                      :class="{ 'playbyplay-followed__live-dot--on': item.isOnCourt }"
                      aria-hidden="true"
                    ></span>
                    <span class="playbyplay-followed__name-text">{{ item.name }}</span>
                  </span>
                  <span class="playbyplay-followed__icon" :class="item.iconClass">{{ item.iconSymbol }}</span>
                  <span class="playbyplay-followed__line">
                    {{ item.line }} {{ item.label }}
                    <span class="playbyplay-followed__current">({{ item.current }})</span>
                    <button
                      class="live-follow__remove"
                      type="button"
                      title="Unfollow"
                      @click.stop="removeFollowedPlayerForGame(group.gameId, item.playerId)"
                    >
                      Unfollow
                    </button>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <aside v-if="activeMainTab === 'live-follow'" class="playbyplay-panel">
        <div v-if="liveFollowGameOptions.length" class="playbyplay-game-tabs">
          <button
            v-for="game in liveFollowGameOptions"
            :key="game.gameId"
            type="button"
            class="playbyplay-game-tab"
            :class="{ 'playbyplay-game-tab--active': game.gameId === selectedLiveFollowGameId }"
            @click="selectedLiveFollowGameId = game.gameId"
          >
            {{ game.label }}
          </button>
        </div>
        <header class="playbyplay-panel__header">
          <div class="playbyplay-header-row">
            <div class="playbyplay-title">
              <h3>{{ playByPlayHeaderLabel }}</h3>
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
            </div>
          </div>
        </header>
        <div v-if="playByPlayPeriods.length" class="playbyplay-tabs-row">
          <div class="playbyplay-tabs">
            <button
              v-for="period in playByPlayPeriods"
              :key="period.period"
              type="button"
              class="playbyplay-tab"
              :class="{ 'playbyplay-tab--active': period.period === selectedPlayByPlayPeriod }"
              @click="selectedPlayByPlayPeriod = period.period"
            >
              {{ period.label }}
            </button>
          </div>
          <span v-if="playByPlayUpdatedText" class="playbyplay-updated">
            {{ playByPlayUpdatedText }}
          </span>
        </div>
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
                <tr
                  v-for="action in filteredPlayByPlayActions"
                  :key="action.orderNumber || action.actionNumber"
                  :class="[
                    getFollowedRowClass(action),
                    { 'playbyplay-row--new': isNewPlayByPlayAction(action) }
                  ]"
                >
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

    <div v-if="followModalOpen" class="follow-modal__backdrop" @click.self="closeFollowModal">
      <div class="follow-modal">
        <header class="follow-modal__header">
          <h3>Seguir odds</h3>
          <p class="muted">{{ followModalPlayer?.name || "Jugador" }}</p>
        </header>
        <div class="follow-modal__body">
          <p class="muted">Selecciona la linea que quieres seguir:</p>
          <div class="follow-modal__options">
            <button
              v-for="option in followModalOptions"
              :key="option.key"
              type="button"
              class="follow-modal__option"
              :class="{ 'follow-modal__option--active': option.key === selectedFollowedOption?.key }"
              @click="selectFollowOption(option)"
            >
              <span class="follow-modal__option-label">{{ option.label }}</span>
              <span class="follow-modal__option-line">
                <span class="follow-modal__option-icon" :class="option.iconClass">{{ option.iconSymbol }}</span>
                {{ option.line }}
              </span>
            </button>
          </div>
          <div class="follow-modal__section">
            <p class="muted">¿Over o under?</p>
            <div class="follow-modal__toggle">
              <button
                type="button"
                class="follow-modal__toggle-button"
                :class="{ 'follow-modal__toggle-button--active': followModalSide === 'over' }"
                :disabled="!selectedFollowedOption"
                @click="followModalSide = 'over'"
              >
                Over
              </button>
              <button
                type="button"
                class="follow-modal__toggle-button"
                :class="{ 'follow-modal__toggle-button--active': followModalSide === 'under' }"
                :disabled="!selectedFollowedOption"
                @click="followModalSide = 'under'"
              >
                Under
              </button>
            </div>
          </div>
          <div class="follow-modal__section">
            <p class="muted">Línea</p>
            <div class="follow-modal__input">
              <input
                v-model="followModalCustomLine"
                type="number"
                step="0.5"
                inputmode="decimal"
                :disabled="!selectedFollowedOption"
                placeholder="Ej: 9.5"
              />
            </div>
            <p v-if="followModalLineError" class="error">{{ followModalLineError }}</p>
          </div>
        </div>
        <footer class="follow-modal__footer">
          <button class="ghost-button" type="button" @click="closeFollowModal">Cancelar</button>
          <button
            class="ghost-button"
            type="button"
            :disabled="!selectedFollowedOption"
            @click="applyFollowSelection"
          >
            Guardar seguimiento
          </button>
          <button
            class="ghost-button ghost-button--danger"
            type="button"
            :disabled="!selectedFollowedPlayer"
            @click="removeFollowSelection"
          >
            Dejar de seguir
          </button>
        </footer>
      </div>
    </div>
  </main>
</template>

<script setup>
import ScheduleHeader from "./components/ScheduleHeader.vue";
import LineupPanel from "./components/LineupPanel.vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { fetchLineupsByDate, fetchLineupByTeams, fetchGameOdds, loadGameLogsForEvent, fetchPlayerGameLogs, fetchPlayerProfile, loadPlayerGameLogs, fetchCdnBoxscore, fetchCdnPlayByPlay } from "./api/endpoints";

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
const activeMainTab = ref("games");
const selectedLiveFollowGameId = ref("");
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
const playByPlayOpen = ref(true);
const playByPlayLoading = ref(false);
const playByPlayError = ref("");
const playByPlay = ref(null);
const playByPlayUpdatedAt = ref(null);
let playByPlayAutoRefreshId = null;
let liveFollowAutoRefreshId = null;
const playByPlayNewActionIds = ref(new Set());
const playByPlayLastActionIds = ref(new Set());
const liveFollowStatsByGame = ref({});
const liveFollowUpdatedAtByGame = ref({});
const liveFollowLastStats = ref({});
const liveFollowPlayByPlayByGame = ref({});

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
  ensureLogsCacheDate(resolveGameDate(game));
  lineup.value = null;
  resolvedGameId.value = "";
  lineupError.value = "";
  oddsRequested.value = false;
  liveStats.value = {};
  playByPlayOpen.value = true;
  playByPlayError.value = "";
  playByPlay.value = null;
  playByPlayUpdatedAt.value = null;
  lastFollowedStats.value = {};
  lastFollowedOnCourt.value = {};
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
      const resolved = await fetchLineupByTeams(
        normalizeTeamTricode(game.homeTricode),
        normalizeTeamTricode(game.awayTricode),
        fallbackDate
      );
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
    oddsRequested.value = Boolean(match?.odds_checked);
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

const hasOddsLinesInLineup = (player) => {
  if (!player) {
    return false;
  }
  const values = [player.points_line, player.rebounds_line, player.assists_line];
  return values.some((value) => value !== null && value !== undefined && !Number.isNaN(value));
};

const isNoOddsMessage = (message) => {
  if (!message) {
    return false;
  }
  return /no .*odds/i.test(message) || /no .*props/i.test(message);
};

const clearOddsFromLineup = (lineupData) => {
  if (!lineupData?.lineups) {
    return lineupData;
  }
  const updated = {
    ...lineupData,
    odds_checked: true,
    lineups: { ...lineupData.lineups }
  };
  Object.entries(updated.lineups).forEach(([teamKey, teamLineup]) => {
    if (!teamLineup) {
      return;
    }
    const nextTeam = { ...teamLineup };
    ["PG", "SG", "SF", "PF", "C"].forEach((position) => {
      const player = nextTeam[position];
      if (player) {
        nextTeam[position] = {
          ...player,
          points_line: null,
          rebounds_line: null,
          assists_line: null,
          has_current_odds: false
        };
      }
    });
    if (Array.isArray(nextTeam.BENCH)) {
      nextTeam.BENCH = nextTeam.BENCH.map((player) => (
        player
          ? {
            ...player,
            points_line: null,
            rebounds_line: null,
            assists_line: null,
            has_current_odds: false
          }
          : player
      ));
    }
    updated.lineups[teamKey] = nextTeam;
  });
  return updated;
};

const persistUpdatedLineup = (updatedLineup) => {
  const gameDate = updatedLineup?.lineup_date || updatedLineup?.game_date;
  const cached = gameDate ? lineupsCache.value[gameDate] : null;
  if (gameDate && Array.isArray(cached)) {
    const idx = cached.findIndex((item) => String(item.game_id) === String(updatedLineup.game_id));
    if (idx !== -1) {
      cached[idx] = updatedLineup;
      persistLineupsCache(lineupsCache.value);
    }
  }
};

const handleLoadOdds = async () => {
  oddsError.value = "";
  const gameId = resolvedGameId.value || lineup.value?.game_id;
  if (!gameId) {
    oddsError.value = "Selecciona un juego con lineup antes de cargar O/U.";
    return;
  }
  oddsRequested.value = true;
  isOddsLoading.value = true;
  try {
    const data = await fetchGameOdds(gameId);
    if (!data?.success) {
      oddsError.value = data?.message || "No se pudieron cargar los odds.";
      if (isNoOddsMessage(data?.message) && lineup.value) {
        lineup.value = clearOddsFromLineup(lineup.value);
        persistUpdatedLineup(lineup.value);
      }
      return;
    }
    if (lineup.value && Array.isArray(data?.matched_players)) {
      const { lineup: updatedLineup, updatedPlayerIds } = applyOddsToLineup(lineup.value, data.matched_players);
      updatedLineup.odds_checked = true;
      lineup.value = updatedLineup;
      persistUpdatedLineup(updatedLineup);
      checkFollowedUpdates();
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
  const gameId = activeMainTab.value === "live-follow"
    ? selectedLiveFollowGameId.value
    : (selectedGame.value?.gameId || resolvedGameId.value || lineup.value?.game_id);
  playByPlayOpen.value = true;
  if (!gameId) {
    playByPlayError.value = "Selecciona un juego antes de cargar el play by play.";
    return;
  }
  if (hasFollowedPlayersForGame(gameId)) {
    if (applyLiveFollowPlayByPlay(gameId)) {
      return;
    }
  }
  if (playByPlayLoading.value) {
    return;
  }
  const wasLoaded = Array.isArray(playByPlayActions.value) && playByPlayActions.value.length > 0;
  if (!wasLoaded) {
    playByPlayLoading.value = true;
  }
  try {
    const data = await fetchCdnPlayByPlay(gameId);
    if (!data?.success) {
      playByPlayError.value = data?.error || "No se pudo cargar el play by play.";
      return;
    }
    const nextPlayByPlay = data.playbyplay || data.playByPlay || data;
    const nextActions = nextPlayByPlay?.game?.actions || nextPlayByPlay?.actions || [];
    const nextIds = new Set(
      Array.isArray(nextActions)
        ? nextActions.map((action) => String(action.orderNumber || action.actionNumber || ""))
        : []
    );
    const previousIds = playByPlayLastActionIds.value;
    const newIds = new Set();
    nextIds.forEach((id) => {
      if (id && !previousIds.has(id)) {
        newIds.add(id);
      }
    });
    playByPlayLastActionIds.value = nextIds;
    playByPlayNewActionIds.value = newIds;
    playByPlay.value = nextPlayByPlay;
    if (newIds.size) {
      setTimeout(() => {
        playByPlayNewActionIds.value = new Set();
      }, 1500);
    }
    try {
      const boxscore = await fetchCdnBoxscore(gameId);
      if (boxscore?.boxscore?.game?.homeTeam || boxscore?.boxscore?.game?.awayTeam) {
        const gameData = boxscore.boxscore.game;
        const home = gameData.homeTeam || {};
        const away = gameData.awayTeam || {};
        liveStats.value = buildLiveStatsMap(
          home.players || [],
          away.players || [],
          home.teamTricode || gameData.homeTeam?.teamTricode,
          away.teamTricode || gameData.awayTeam?.teamTricode
        );
        checkFollowedUpdates();
      }
    } catch {
      // ignore boxscore refresh errors
    }
    const periods = playByPlayPeriods.value;
    selectedPlayByPlayPeriod.value = periods.length ? periods[periods.length - 1].period : null;
    playByPlayUpdatedAt.value = new Date();
  } catch (err) {
    if (!wasLoaded) {
      playByPlayError.value = err?.message || "Error inesperado al cargar el play by play.";
    }
  } finally {
    playByPlayLoading.value = false;
  }
};

const playByPlayTeams = computed(() => {
  const game = activePlayByPlayGame.value || {};
  const home = game?.homeTricode
    || game?.homeTeam?.teamTricode
    || game?.homeTeamTricode
    || "";
  const away = game?.awayTricode
    || game?.awayTeam?.teamTricode
    || game?.awayTeamTricode
    || "";
  return { home, away };
});

const playByPlayIsLive = computed(() => {
  const status = Number(activePlayByPlayGame.value?.gameStatus);
  return !Number.isNaN(status) && status >= 2 && status !== 3;
});

const playByPlayUpdatedLabel = computed(() => {
  if (!playByPlayUpdatedAt.value) {
    return "";
  }
  const raw = playByPlayUpdatedAt.value.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit"
  });
  return raw
    .toLowerCase()
    .replace(" am", ".am")
    .replace(" pm", ".pm");
});

const playByPlayUpdatedText = computed(() => (
  playByPlayUpdatedLabel.value ? `Last update: ${playByPlayUpdatedLabel.value}` : ""
));

const formatLiveFollowUpdatedLabel = (value) => {
  if (!value) {
    return "";
  }
  const raw = value.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  return raw.toLowerCase().replace(" am", ".am").replace(" pm", ".pm");
};

const playByPlayHeaderLabel = computed(() => {
  const latestAction = playByPlayActions.value[0];
  if (!latestAction) {
    return "Play by Play";
  }
  const periodLabel = getPeriodLabel(latestAction?.period);
  const clockLabel = formatPlayClock(latestAction?.clock);
  return `${periodLabel} ${clockLabel}`.trim();
});

const playByPlayActions = computed(() => {
  const actions = playByPlay.value?.game?.actions || playByPlay.value?.actions || [];
  if (!Array.isArray(actions)) {
    return [];
  }
  return [...actions].sort((a, b) => (b.orderNumber || 0) - (a.orderNumber || 0));
});

const isNewPlayByPlayAction = (action) => {
  const id = String(action?.orderNumber || action?.actionNumber || "");
  return id ? playByPlayNewActionIds.value.has(id) : false;
};

const getPeriodLabel = (period) => {
  const number = Number(period);
  if (!number) {
    return "Periodo";
  }
  if (number <= 4) {
    return `Q${number}`;
  }
  return `OT${number - 4}`;
};

const playByPlayPeriods = computed(() => {
  const periods = new Map();
  playByPlayActions.value.forEach((action) => {
    const period = Number(action?.period) || 0;
    if (!periods.has(period)) {
      periods.set(period, getPeriodLabel(period));
    }
  });
  return [...periods.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([period, label]) => ({ period, label }));
});

const selectedPlayByPlayPeriod = ref(null);

const filteredPlayByPlayActions = computed(() => {
  if (!selectedPlayByPlayPeriod.value) {
    return playByPlayActions.value;
  }
  return playByPlayActions.value.filter(
    (action) => Number(action?.period) === Number(selectedPlayByPlayPeriod.value)
  );
});

const isTimeoutAction = (action) => {
  if (!action) {
    return false;
  }
  const actionType = String(action.actionType || "").toLowerCase();
  const subType = String(action.subType || "").toLowerCase();
  const description = String(action.description || action.actionText || action.detail || "").toLowerCase();
  return actionType.includes("timeout") || subType.includes("timeout") || description.includes("timeout");
};

const timeoutLabel = computed(() => {
  const latestAction = playByPlayActions.value[0];
  return latestAction && isTimeoutAction(latestAction) ? "TIMEOUT" : "";
});

const FOLLOWED_PLAYERS_KEY = "livenba_followed_players";
const loadFollowedPlayers = () => {
  try {
    const stored = localStorage.getItem(FOLLOWED_PLAYERS_KEY);
    const parsed = stored ? JSON.parse(stored) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
};

const saveFollowedPlayers = (playersByGame) => {
  try {
    localStorage.setItem(FOLLOWED_PLAYERS_KEY, JSON.stringify(playersByGame));
  } catch {
    // ignore storage errors
  }
};

const followedPlayersByGame = ref(loadFollowedPlayers());

const currentGameKey = computed(() => (
  selectedGameId.value
  || resolvedGameId.value
  || lineup.value?.game_id
  || ""
));

const followedPlayers = computed(() => {
  const key = currentGameKey.value;
  return key ? (followedPlayersByGame.value[key] || []) : [];
});

const setFollowedPlayersForGame = (players) => {
  const key = currentGameKey.value;
  if (!key) {
    return;
  }
  followedPlayersByGame.value = {
    ...followedPlayersByGame.value,
    [key]: players
  };
  saveFollowedPlayers(followedPlayersByGame.value);
};

const removeFollowedPlayerForGame = (gameId, playerId) => {
  if (!gameId || !playerId) {
    return;
  }
  const key = String(gameId);
  const existing = followedPlayersByGame.value?.[key] || [];
  const next = existing.filter((item) => String(item?.playerId || "") !== String(playerId));
  followedPlayersByGame.value = {
    ...followedPlayersByGame.value,
    [key]: next
  };
  saveFollowedPlayers(followedPlayersByGame.value);
};

const liveFollowGames = computed(() => (
  scheduleGames.value.filter((game) => Boolean(game?.isLive))
));

const liveFollowGroups = computed(() => {
  const followedByGame = followedPlayersByGame.value || {};
  return liveFollowGames.value
    .map((game) => {
      const followed = followedByGame[game.gameId] || [];
      if (!followed.length) {
        return null;
      }
      const statsMap = liveFollowStatsByGame.value[game.gameId] || null;
      const items = followed
        .filter((item) => item?.statKey)
        .map((item) => {
          const current = getFollowedCurrentValueFromStats(statsMap, item.playerId, item.statKey);
          const live = statsMap?.byId?.[item.playerId] || null;
          const isOnCourt = ["1", "true", true, 1].includes(live?.oncourt);
          const side = item.side === "under" ? "under" : item.side === "over" ? "over" : null;
          return {
            key: `${game.gameId}-${item.playerId}-${item.statKey}`,
            playerId: item.playerId,
            name: item.name || "Jugador",
            label: item.label || "",
            line: item.line ?? "",
            iconSymbol: side ? (side === "under" ? "▼" : "▲") : (item.iconSymbol || ""),
            iconClass: side ? (side === "under" ? "indicator--under" : "indicator--over") : (item.iconClass || ""),
            current: current ?? "--",
            isOnCourt
          };
        });
      const updatedAt = liveFollowUpdatedAtByGame.value[game.gameId] || null;
      const awayScore = game.awayScore ?? game.awayRecord ?? null;
      const homeScore = game.homeScore ?? game.homeRecord ?? null;
      const scoreLabel = (awayScore !== null && homeScore !== null)
        ? `${awayScore} - ${homeScore}`
        : "";
      return {
        gameId: game.gameId,
        timeLabel: game.time || "",
        matchup: `${game.awayTricode || game.awayName || "AWAY"} vs ${game.homeTricode || game.homeName || "HOME"}`,
        updatedLabel: updatedAt ? formatLiveFollowUpdatedLabel(updatedAt) : "",
        scoreLabel,
        items
      };
    })
    .filter((group) => group && group.items.length);
});

const liveFollowGameOptions = computed(() => (
  liveFollowGroups.value.map((group) => ({
    gameId: group.gameId,
    label: group.matchup
  }))
));

const scheduleGameById = computed(() => (
  scheduleGames.value.reduce((acc, game) => {
    if (game?.gameId) {
      acc[String(game.gameId)] = game;
    }
    return acc;
  }, {})
));

const activePlayByPlayGame = computed(() => {
  if (activeMainTab.value === "live-follow") {
    return scheduleGameById.value[String(selectedLiveFollowGameId.value)] || null;
  }
  return selectedGame.value;
});

watch(activeMainTab, (next) => {
  if (next === "live-follow") {
    refreshLiveFollowData();
  }
  if (next === "games") {
    selectedLiveFollowGameId.value = "";
  }
});

watch(liveFollowGroups, (groups) => {
  if (!groups.length) {
    selectedLiveFollowGameId.value = "";
    return;
  }
  if (!selectedLiveFollowGameId.value) {
    selectedLiveFollowGameId.value = groups[0].gameId;
  }
});

watch(selectedLiveFollowGameId, (next) => {
  if (activeMainTab.value !== "live-follow") {
    return;
  }
  if (next) {
    applyLiveFollowPlayByPlay(next);
  }
});

const followModalOpen = ref(false);
const followModalPlayer = ref(null);
const followModalOptions = ref([]);
const followModalSelectedOption = ref(null);
const followModalSide = ref("over");
const followModalUseCustomLine = ref(true);
const followModalCustomLine = ref("");
const followModalLineError = ref("");
const lastFollowedStats = ref({});
const lastFollowedOnCourt = ref({});
let followAlertAudioContext = null;
const FOLLOW_ALERT_VOLUME = 0.45;

const handleFollowRequest = (player) => {
  if (!player?.playerId) {
    return;
  }
  const options = getPlayerFollowOptions(player);
  if (!options.length) {
    return;
  }
  const id = String(player.playerId);
  const existing = followedPlayers.value.find((item) => String(item.playerId) === id) || null;
  const existingOption = existing?.statKey
    ? options.find((option) => option.key === existing.statKey)
    : null;
  followModalPlayer.value = player;
  followModalOptions.value = options;
  followModalSelectedOption.value = existingOption || null;
  followModalSide.value = existing?.side === "under" ? "under" : "over";
  followModalUseCustomLine.value = true;
  followModalCustomLine.value = String(existing?.line ?? existingOption?.line ?? "");
  followModalLineError.value = "";
  followModalOpen.value = true;
};

const closeFollowModal = () => {
  followModalOpen.value = false;
  followModalPlayer.value = null;
  followModalOptions.value = [];
  followModalSelectedOption.value = null;
  followModalSide.value = "over";
  followModalUseCustomLine.value = true;
  followModalCustomLine.value = "";
  followModalLineError.value = "";
};

const selectFollowOption = (option) => {
  followModalSelectedOption.value = option;
  if (option?.line !== null && option?.line !== undefined) {
    followModalCustomLine.value = String(option.line);
  }
  followModalLineError.value = "";
};

const parseCustomLine = (value) => {
  const normalized = String(value || "").trim().replace(",", ".");
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
};

const playFollowTone = ({ startFreq, endFreq, duration, volume, type = "sine" }) => {
  try {
    if (!followAlertAudioContext) {
      followAlertAudioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (followAlertAudioContext.state === "suspended") {
      followAlertAudioContext.resume().catch(() => undefined);
    }
    const now = followAlertAudioContext.currentTime;
    const oscillator = followAlertAudioContext.createOscillator();
    const gain = followAlertAudioContext.createGain();
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(startFreq, now);
    oscillator.frequency.exponentialRampToValueAtTime(endFreq, now + duration * 0.55);
    gain.gain.setValueAtTime(0.001, now);
    gain.gain.exponentialRampToValueAtTime(volume, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
    oscillator.connect(gain);
    gain.connect(followAlertAudioContext.destination);
    oscillator.start(now);
    oscillator.stop(now + duration + 0.02);
  } catch {
    // ignore audio playback errors
  }
};

const playFollowStatSound = () => {
  playFollowTone({ startFreq: 880, endFreq: 660, duration: 0.22, volume: FOLLOW_ALERT_VOLUME });
};

const playFollowEnterSound = () => {
  playFollowTone({ startFreq: 1200, endFreq: 1600, duration: 0.18, volume: FOLLOW_ALERT_VOLUME });
};

const playFollowBenchSound = () => {
  playFollowTone({ startFreq: 420, endFreq: 260, duration: 0.24, volume: FOLLOW_ALERT_VOLUME });
};

const getFollowedCurrentValue = (playerId, statKey) => {
  const live = liveStats.value?.byId?.[playerId] || null;
  const current = statKey === "points"
    ? live?.pts
    : statKey === "rebounds"
      ? live?.reb
      : statKey === "assists"
        ? live?.ast
        : null;
  const numeric = Number(current);
  return Number.isFinite(numeric) ? numeric : null;
};

const getFollowedCurrentValueFromStats = (statsMap, playerId, statKey) => {
  const live = statsMap?.byId?.[playerId] || null;
  const current = statKey === "points"
    ? live?.pts
    : statKey === "rebounds"
      ? live?.reb
      : statKey === "assists"
        ? live?.ast
        : null;
  const numeric = Number(current);
  return Number.isFinite(numeric) ? numeric : null;
};

const checkFollowedUpdates = () => {
  const players = followedPlayers.value || [];
  if (!players.length) {
    return;
  }
  const nextSnapshot = { ...lastFollowedStats.value };
  const nextOnCourt = { ...lastFollowedOnCourt.value };
  let statChanged = false;
  let entered = false;
  let benched = false;

  players.forEach((player) => {
    if (!player?.playerId || !player?.statKey) {
      return;
    }
    const key = `${player.playerId}-${player.statKey}`;
    const current = getFollowedCurrentValue(player.playerId, player.statKey);
    if (current == null) {
      // still track on-court/line even if stat is missing
    } else {
      if (nextSnapshot[key] != null && Number(nextSnapshot[key]) !== current) {
        statChanged = true;
      }
      nextSnapshot[key] = current;
    }

    const live = liveStats.value?.byId?.[player.playerId] || null;
    if (live?.oncourt !== undefined && live?.oncourt !== null) {
      const isOnCourt = ["1", "true", true, 1].includes(live.oncourt);
      const previousOnCourt = nextOnCourt[player.playerId];
      if (previousOnCourt !== undefined && previousOnCourt !== null && previousOnCourt !== isOnCourt) {
        if (isOnCourt) {
          entered = true;
        } else {
          benched = true;
        }
      }
      nextOnCourt[player.playerId] = isOnCourt;
    }

  });

  lastFollowedStats.value = nextSnapshot;
  lastFollowedOnCourt.value = nextOnCourt;
  if (entered) {
    playFollowEnterSound();
  }
  if (benched) {
    playFollowBenchSound();
  }
  if (statChanged) {
    playFollowStatSound();
  }
};

const hasFollowedPlayersForGame = (gameId) => {
  if (!gameId) {
    return false;
  }
  const followed = followedPlayersByGame.value?.[gameId] || [];
  return followed.length > 0;
};

const applyLiveFollowPlayByPlay = (gameId) => {
  const cached = liveFollowPlayByPlayByGame.value?.[gameId];
  if (!cached) {
    return false;
  }
  playByPlay.value = cached;
  playByPlayUpdatedAt.value = liveFollowUpdatedAtByGame.value?.[gameId] || new Date();
  const actions = cached?.game?.actions || cached?.actions || [];
  if (Array.isArray(actions)) {
    const ids = new Set(actions.map((action) => String(action?.orderNumber || action?.actionNumber || "")));
    playByPlayNewActionIds.value = ids;
    playByPlayLastActionIds.value = ids;
  }
  return true;
};

const refreshLiveFollowData = async () => {
  const games = liveFollowGames.value;
  if (!games.length) {
    return;
  }
  const nextStatsByGame = { ...liveFollowStatsByGame.value };
  const nextUpdatedAt = { ...liveFollowUpdatedAtByGame.value };
  const nextLastStats = { ...liveFollowLastStats.value };
  const nextPlayByPlayByGame = { ...liveFollowPlayByPlayByGame.value };
  let statChanged = false;

  await Promise.all(games.map(async (game) => {
    const followed = followedPlayersByGame.value?.[game.gameId] || [];
    if (!followed.length) {
      return;
    }
    try {
      const boxscore = await fetchCdnBoxscore(game.gameId);
      const gameData = boxscore?.boxscore?.game;
      if (gameData?.homeTeam || gameData?.awayTeam) {
        const home = gameData.homeTeam || {};
        const away = gameData.awayTeam || {};
        nextStatsByGame[game.gameId] = buildLiveStatsMap(
          home.players || [],
          away.players || [],
          home.teamTricode || gameData.homeTeam?.teamTricode,
          away.teamTricode || gameData.awayTeam?.teamTricode
        );
      }
    } catch {
      // ignore boxscore refresh errors
    }

    try {
      const pbpResponse = await fetchCdnPlayByPlay(game.gameId);
      if (pbpResponse?.success === false) {
        return;
      }
      const nextPlayByPlay = pbpResponse?.playbyplay || pbpResponse?.playByPlay || pbpResponse;
      if (nextPlayByPlay?.game || nextPlayByPlay?.actions) {
        nextUpdatedAt[game.gameId] = new Date();
        nextStatsByGame[game.gameId] = nextStatsByGame[game.gameId] || null;
        nextPlayByPlayByGame[game.gameId] = nextPlayByPlay;
      }
    } catch {
      // ignore play by play refresh errors
    }

    const statsMap = nextStatsByGame[game.gameId] || null;
    if (!statsMap) {
      return;
    }
    followed.forEach((player) => {
      if (!player?.playerId || !player?.statKey) {
        return;
      }
      const key = `${game.gameId}-${player.playerId}-${player.statKey}`;
      const current = getFollowedCurrentValueFromStats(statsMap, player.playerId, player.statKey);
      if (current == null) {
        return;
      }
      if (nextLastStats[key] != null && Number(nextLastStats[key]) !== Number(current)) {
        statChanged = true;
      }
      nextLastStats[key] = current;
    });
  }));

  liveFollowStatsByGame.value = nextStatsByGame;
  liveFollowUpdatedAtByGame.value = nextUpdatedAt;
  liveFollowLastStats.value = nextLastStats;
  liveFollowPlayByPlayByGame.value = nextPlayByPlayByGame;
  if (statChanged) {
    playFollowStatSound();
  }
};

const applyFollowSelection = () => {
  const player = followModalPlayer.value;
  const option = followModalSelectedOption.value;
  if (!player?.playerId || !option) {
    closeFollowModal();
    return;
  }
  let lineValue = option.line ?? null;
  if (followModalUseCustomLine.value) {
    const parsedLine = parseCustomLine(followModalCustomLine.value);
    if (parsedLine == null) {
      followModalLineError.value = "Ingresa una línea válida.";
      return;
    }
    lineValue = parsedLine;
  }
  followModalLineError.value = "";
  const id = String(player.playerId);
  const next = [...followedPlayers.value];
  const idx = next.findIndex((item) => String(item.playerId) === id);
  const side = followModalSide.value === "under" ? "under" : "over";
  const payload = {
    playerId: player.playerId,
    name: player.name || "",
    statKey: option.key,
    label: option.label,
    line: lineValue,
    lineSource: followModalUseCustomLine.value ? "custom" : "market",
    side,
    iconSymbol: side === "under" ? "▼" : "▲",
    iconClass: side === "under" ? "indicator--under" : "indicator--over"
  };
  if (idx >= 0) {
    next[idx] = payload;
  } else {
    next.push(payload);
  }
  setFollowedPlayersForGame(next);
  closeFollowModal();
};

const removeFollowSelection = () => {
  const player = followModalPlayer.value;
  if (!player?.playerId) {
    closeFollowModal();
    return;
  }
  const id = String(player.playerId);
  const next = followedPlayers.value.filter((item) => String(item.playerId) !== id);
  setFollowedPlayersForGame(next);
  closeFollowModal();
};

const getPlayerFollowOptions = (player) => {
  const options = [];
  if (player.pointsLine != null) {
    options.push({
      key: "points",
      label: "PTS",
      line: player.pointsLine,
      iconSymbol: player.pointsIndicator?.symbol || "",
      iconClass: player.pointsIndicator?.className || ""
    });
  }
  if (player.reboundsLine != null) {
    options.push({
      key: "rebounds",
      label: "REB",
      line: player.reboundsLine,
      iconSymbol: player.reboundsIndicator?.symbol || "",
      iconClass: player.reboundsIndicator?.className || ""
    });
  }
  if (player.assistsLine != null) {
    options.push({
      key: "assists",
      label: "AST",
      line: player.assistsLine,
      iconSymbol: player.assistsIndicator?.symbol || "",
      iconClass: player.assistsIndicator?.className || ""
    });
  }
  return options;
};

const followedHeaderItems = computed(() => (followedPlayers.value || [])
  .filter((item) => item?.statKey)
  .map((item) => {
    const live = liveStats.value?.byId?.[item.playerId] || null;
    const statKey = item.statKey;
    const current = statKey === "points"
      ? live?.pts
      : statKey === "rebounds"
        ? live?.reb
        : statKey === "assists"
          ? live?.ast
          : null;
    const isOnCourt = ["1", "true", true, 1].includes(live?.oncourt);
    const side = item.side === "under" ? "under" : item.side === "over" ? "over" : null;
    return {
      key: `${item.playerId}-${item.statKey}`,
      name: item.name || "Jugador",
      label: item.label || "",
      line: item.line ?? "",
      iconSymbol: side ? (side === "under" ? "▼" : "▲") : (item.iconSymbol || ""),
      iconClass: side ? (side === "under" ? "indicator--under" : "indicator--over") : (item.iconClass || ""),
      current: current ?? "--",
      isOnCourt
    };
  }));

const normalizeText = (value) => String(value || "")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase()
  .replace(/[^a-z0-9\s.-]/g, " ")
  .replace(/\s+/g, " ")
  .trim();

const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const FOLLOWED_COLORS = [
  "playbyplay-row--followed-a",
  "playbyplay-row--followed-b",
  "playbyplay-row--followed-c",
  "playbyplay-row--followed-d",
  "playbyplay-row--followed-e",
  "playbyplay-row--followed-f"
];

const followedMatchers = computed(() => {
  const players = followedPlayers.value || [];
  const lastNameCounts = players.reduce((acc, player) => {
    const name = normalizeText(player?.name || "");
    const parts = name.split(" ").filter(Boolean);
    const lastName = parts.length ? parts[parts.length - 1] : "";
    if (lastName) {
      acc[lastName] = (acc[lastName] || 0) + 1;
    }
    return acc;
  }, {});

  return players.map((player, index) => {
    const name = normalizeText(player?.name || "");
    const parts = name.split(" ").filter(Boolean);
    const firstName = parts[0] || "";
    const lastName = parts.length ? parts[parts.length - 1] : "";
    const tokens = [];
    if (name) {
      tokens.push(name);
    }
    if (firstName && lastName) {
      tokens.push(`${firstName} ${lastName}`);
    }
    if (lastName && lastNameCounts[lastName] === 1) {
      tokens.push(lastName);
    }
    const regexes = tokens.map((token) => new RegExp(`\\b${escapeRegex(token)}\\b`, "i"));
    const colorClass = FOLLOWED_COLORS[index % FOLLOWED_COLORS.length];
    return { playerId: player.playerId, regexes, colorClass };
  });
});

const getFollowedRowClass = (action) => {
  const text = normalizeText(action?.description || action?.actionText || action?.detail || "");
  if (!text) {
    return "";
  }
  const match = followedMatchers.value.find((matcher) => matcher.regexes.some((regex) => regex.test(text)));
  return match?.colorClass || "";
};

const selectedFollowedOption = computed(() => {
  if (followModalSelectedOption.value) {
    return followModalSelectedOption.value;
  }
  const player = followModalPlayer.value;
  if (!player?.playerId) {
    return null;
  }
  const id = String(player.playerId);
  const existing = followedPlayers.value.find((item) => String(item.playerId) === id);
  if (!existing?.statKey) {
    return null;
  }
  return followModalOptions.value.find((option) => option.key === existing.statKey) || null;
});

const selectedFollowedPlayer = computed(() => {
  const player = followModalPlayer.value;
  if (!player?.playerId) {
    return null;
  }
  const id = String(player.playerId);
  return followedPlayers.value.find((item) => String(item.playerId) === id) || null;
});

const parsePlayClockSeconds = (clock) => {
  if (!clock) {
    return null;
  }
  const match = /PT(\d+)M(\d+)\.(\d+)S/.exec(clock);
  if (!match) {
    return null;
  }
  const minutes = Number(match[1]);
  const seconds = Number(match[2]);
  if (Number.isNaN(minutes) || Number.isNaN(seconds)) {
    return null;
  }
  return minutes * 60 + seconds;
};

const getPeriodLengthSeconds = (period) => (period && period > 4 ? 300 : 720);

const getElapsedSeconds = (action) => {
  const period = Number(action?.period);
  if (!period) {
    return null;
  }
  const remaining = parsePlayClockSeconds(action?.clock);
  if (remaining === null) {
    return null;
  }
  const periodLength = getPeriodLengthSeconds(period);
  const previousReg = Math.min(period - 1, 4);
  const previousOt = Math.max(period - 5, 0);
  const previousSeconds = previousReg * 720 + previousOt * 300;
  const elapsedInPeriod = Math.max(0, periodLength - remaining);
  return previousSeconds + elapsedInPeriod;
};

const extractSubNames = (action) => {
  const description = String(action?.description || action?.actionText || action?.detail || "").trim();
  if (!description) {
    return { inName: "", outName: "" };
  }
  const normalized = description.replace(/\s+/g, " ");
  const match = /sub[:\s]+(.+?)\s+for\s+(.+)/i.exec(normalized);
  if (match) {
    return { inName: match[1].trim(), outName: match[2].trim() };
  }
  return { inName: "", outName: "" };
};

const isSubAction = (action) => {
  const type = String(action?.actionType || "").toLowerCase();
  const subType = String(action?.subType || "").toLowerCase();
  const desc = String(action?.description || action?.actionText || "").toLowerCase();
  return type.includes("sub") || subType.includes("sub") || desc.includes("sub");
};

const playByPlaySubs = computed(() => {
  const actions = playByPlayActions.value;
  const result = { byId: {}, byName: {}, currentElapsed: null };
  if (!actions.length) {
    return result;
  }
  const currentElapsed = getElapsedSeconds(actions[0]);
  result.currentElapsed = currentElapsed;
  const chronological = [...actions].sort((a, b) => (a.orderNumber || 0) - (b.orderNumber || 0));

  const ensureEntry = (bucket, key) => {
    if (!key) {
      return null;
    }
    if (!bucket[key]) {
      bucket[key] = { subsIn: 0, subsOut: 0, lastInElapsed: null, lastOutElapsed: null };
    }
    return bucket[key];
  };

  chronological.forEach((action) => {
    if (!isSubAction(action)) {
      return;
    }
    const elapsed = getElapsedSeconds(action);
    const subType = String(action?.subType || "").toLowerCase();
    const { inName, outName } = extractSubNames(action);
    const personId = action?.personId ? String(action.personId) : "";

    if (subType === "in") {
      const entry = ensureEntry(result.byId, personId);
      if (entry) {
        entry.subsIn += 1;
        entry.lastInElapsed = elapsed;
      }
      const key = normalizeName(inName);
      const nameEntry = ensureEntry(result.byName, key);
      if (nameEntry) {
        nameEntry.subsIn += 1;
        nameEntry.lastInElapsed = elapsed;
      }
      return;
    }
    if (subType === "out") {
      const entry = ensureEntry(result.byId, personId);
      if (entry) {
        entry.subsOut += 1;
        entry.lastOutElapsed = elapsed;
      }
      const key = normalizeName(outName);
      const nameEntry = ensureEntry(result.byName, key);
      if (nameEntry) {
        nameEntry.subsOut += 1;
        nameEntry.lastOutElapsed = elapsed;
      }
      return;
    }

    if (inName || outName) {
      const inKey = normalizeName(inName);
      const outKey = normalizeName(outName);
      const inEntry = ensureEntry(result.byName, inKey);
      if (inEntry) {
        inEntry.subsIn += 1;
        inEntry.lastInElapsed = elapsed;
      }
      const outEntry = ensureEntry(result.byName, outKey);
      if (outEntry) {
        outEntry.subsOut += 1;
        outEntry.lastOutElapsed = elapsed;
      }
    }
  });

  return result;
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
    NOP: "NO",
    NO: "NO",
    NYK: "NY",
    NY: "NY",
    GSW: "GS",
    GS: "GS",
    PHX: "PHO",
    PHO: "PHO",
    SAS: "SA",
    SA: "SA"
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
    target.has_current_odds = hasOddsLinesInLineup(target);
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
      has_current_odds: hasOddsLinesInLineup(player),
      over_under_history: player.over_under_history,
      oddsFlash: true
    });
    if (player.player_id) {
      updatedPlayerIds.add(String(player.player_id));
    }
  });

  Object.values(updated.lineups).forEach((teamLineup) => {
    if (!teamLineup) {
      return;
    }
    ["PG", "SG", "SF", "PF", "C"].forEach((position) => {
      const player = teamLineup[position];
      if (player) {
        player.has_current_odds = hasOddsLinesInLineup(player);
      }
    });
    if (Array.isArray(teamLineup.BENCH)) {
      teamLineup.BENCH.forEach((player) => {
        if (player) {
          player.has_current_odds = hasOddsLinesInLineup(player);
        }
      });
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
  playByPlayAutoRefreshId = setInterval(() => {
    if (activeMainTab.value !== "live-follow") {
      return;
    }
    const gameId = selectedLiveFollowGameId.value;
    if (!gameId || playByPlayLoading.value) {
      return;
    }
    handleLoadPlayByPlay();
  }, 10000);
  liveFollowAutoRefreshId = setInterval(() => {
    refreshLiveFollowData();
  }, 10000);
});

onUnmounted(() => {
  if (playByPlayAutoRefreshId) {
    clearInterval(playByPlayAutoRefreshId);
  }
  if (liveFollowAutoRefreshId) {
    clearInterval(liveFollowAutoRefreshId);
  }
});

const GAME_LOGS_CACHE_KEY = "livenba_game_logs_cache";
const gameLogsCache = new Map();
const profileCache = new Map();
const minutesAvgByPlayer = ref({});
let gameLogsCacheDate = "";

const loadLogsCache = () => {
  try {
    const stored = localStorage.getItem(GAME_LOGS_CACHE_KEY);
    if (!stored) {
      return;
    }
    const parsed = JSON.parse(stored);
    const date = parsed?.date || "";
    const today = getTodayInLATimezone();
    if (!date || date !== today) {
      return;
    }
    gameLogsCacheDate = date;
    const logs = parsed?.logs || {};
    const profiles = parsed?.profiles || {};
    const minutesAvg = parsed?.minutesAvg || {};
    Object.entries(logs).forEach(([key, value]) => gameLogsCache.set(key, value));
    Object.entries(profiles).forEach(([key, value]) => profileCache.set(key, value));
    minutesAvgByPlayer.value = minutesAvg;
  } catch {
    // ignore cache read errors
  }
};

const persistLogsCache = () => {
  try {
    const logs = Object.fromEntries(gameLogsCache.entries());
    const profiles = Object.fromEntries(profileCache.entries());
    const minutesAvg = minutesAvgByPlayer.value || {};
    localStorage.setItem(GAME_LOGS_CACHE_KEY, JSON.stringify({
      date: gameLogsCacheDate,
      logs,
      profiles,
      minutesAvg
    }));
  } catch {
    // ignore cache write errors
  }
};

const clearLogsCache = (nextDate) => {
  gameLogsCache.clear();
  profileCache.clear();
  minutesAvgByPlayer.value = {};
  gameLogsCacheDate = nextDate || "";
  persistLogsCache();
};

const ensureLogsCacheDate = (date) => {
  const target = date || getTodayInLATimezone();
  if (!gameLogsCacheDate) {
    gameLogsCacheDate = target;
    persistLogsCache();
    return;
  }
  if (gameLogsCacheDate !== target) {
    clearLogsCache(target);
  }
};

loadLogsCache();

const getCacheKey = (player) => String(player?.playerId || "");

const handleShowLogs = async (player) => {
  if (!player?.playerId) {
    return;
  }
  ensureLogsCacheDate(resolveGameDate(selectedGame.value));
  const popup = openLogsWindow(player?.name || "Game Logs");
  renderLoading(popup);
  try {
    const withTimeout = (promise, timeoutMs) => Promise.race([
      promise,
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Tiempo de espera agotado")), timeoutMs);
      })
    ]);

    const cacheKey = getCacheKey(player);
    const cachedLogs = cacheKey ? gameLogsCache.get(cacheKey) : null;
    const cachedProfile = cacheKey ? profileCache.get(cacheKey) : null;
    if (cachedLogs) {
      renderLogs(popup, player, cachedLogs, cachedProfile);
      return;
    }

    const defender = getDefenderForPlayer(player, lineup.value);
    const profilePromise = cachedProfile
      ? Promise.resolve(cachedProfile)
      : fetchPlayerProfile(player.playerId, player.name).catch(() => null);
    const defenderProfilePromise = defender
      ? fetchPlayerProfile(defender.player_id, defender.player_name).catch(() => null)
      : Promise.resolve(null);
    let data = await fetchPlayerGameLogs(player.playerId, player.name);
    if (data?.success && Array.isArray(data.game_logs) && data.game_logs.length === 0) {
      const loadResult = await withTimeout(
        loadPlayerGameLogs(player.playerId, player.name),
        20000
      );
      if (!loadResult?.success) {
        renderError(popup, loadResult?.message || "No se pudieron cargar los game logs desde NBA API.");
        return;
      }
      data = await fetchPlayerGameLogs(player.playerId, player.name);
    }
    if (!data?.success) {
      renderError(popup, data?.message || "No se pudieron cargar los game logs.");
      return;
    }
    const profileData = await profilePromise;
    const defenderProfile = await defenderProfilePromise;
    const logsPayload = data.game_logs || [];
    if (cacheKey) {
      gameLogsCache.set(cacheKey, logsPayload);
      if (profileData) {
        profileCache.set(cacheKey, profileData?.profile || profileData);
      }
      const avgMinutes = getAverageMinutes(logsPayload);
      if (avgMinutes !== null) {
        minutesAvgByPlayer.value = {
          ...minutesAvgByPlayer.value,
          [cacheKey]: avgMinutes
        };
      }
      persistLogsCache();
    }
    renderLogs(popup, player, logsPayload, profileData?.profile || profileData, defender, defenderProfile?.profile || defenderProfile);
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

const formatTraitValue = (value, suffix = "") => {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  if (Number.isFinite(Number(value)) && suffix) {
    return `${Number(value)}${suffix}`;
  }
  return String(value);
};

const parseMinutesValue = (value) => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }
  const text = String(value).trim();
  if (!text) {
    return null;
  }
  if (text.includes(":")) {
    const [mins, secs] = text.split(":").map((part) => Number(part));
    if (!Number.isNaN(mins) && !Number.isNaN(secs)) {
      return mins + secs / 60;
    }
  }
  const numeric = Number(text.replace(/[^\d.]/g, ""));
  return Number.isNaN(numeric) ? null : numeric;
};

const getAverageMinutes = (logs) => {
  if (!Array.isArray(logs) || logs.length === 0) {
    return null;
  }
  const values = logs
    .map((log) => parseMinutesValue(log?.minutes_played ?? log?.minutes ?? log?.min))
    .filter((value) => value !== null);
  if (!values.length) {
    return null;
  }
  const sum = values.reduce((acc, value) => acc + value, 0);
  return sum / values.length;
};

const parseHeightToInches = (value) => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }
  const match = String(value).match(/(\d+)\s*-\s*(\d+)/);
  if (match) {
    return Number(match[1]) * 12 + Number(match[2]);
  }
  const numeric = Number(String(value).replace(/[^\d.]/g, ""));
  return Number.isNaN(numeric) ? null : numeric;
};

const parseWeight = (value) => {
  if (value === null || value === undefined) {
    return null;
  }
  const numeric = Number(String(value).replace(/[^\d.]/g, ""));
  return Number.isNaN(numeric) ? null : numeric;
};

const buildMismatchSummary = (playerProfile, defenderProfile) => {
  if (!playerProfile || !defenderProfile) {
    return { score: null, note: "Sin datos del defensor." };
  }
  const playerHeight = parseHeightToInches(playerProfile.height);
  const defenderHeight = parseHeightToInches(defenderProfile.height);
  const playerWeight = parseWeight(playerProfile.weight);
  const defenderWeight = parseWeight(defenderProfile.weight);

  const heightDiff = playerHeight !== null && defenderHeight !== null ? playerHeight - defenderHeight : 0;
  const weightDiff = playerWeight !== null && defenderWeight !== null ? playerWeight - defenderWeight : 0;

  let score = 50;
  score += heightDiff * 3;
  score += weightDiff / 5;
  score = Math.max(0, Math.min(100, Math.round(score)));

  let note = "Sin ventaja clara.";
  if (heightDiff >= 2 || weightDiff >= 15) {
    note = "Ventaja fisica en el emparejamiento.";
  } else if (heightDiff <= -2 || weightDiff <= -15) {
    note = "Desventaja fisica en el emparejamiento.";
  }

  return { score, note };
};

const getDefenderForPlayer = (player, lineupData) => {
  if (!player || !lineupData?.lineups) {
    return null;
  }
  const playerTeam = player.teamKey;
  const awayKey = lineupData.away_team;
  const homeKey = lineupData.home_team;
  const opponentKey = playerTeam === awayKey ? homeKey : playerTeam === homeKey ? awayKey : "";
  const position = player.position;
  if (!opponentKey || !position || position === "BENCH") {
    return null;
  }
  const opponentLineup = lineupData.lineups?.[opponentKey];
  const defender = opponentLineup?.[position];
  if (!defender) {
    return null;
  }
  return { ...defender, teamKey: opponentKey };
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

const renderLogs = (popup, player, logs, profile, defender, defenderProfile) => {
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

  const traits = profile?.profile || profile || {};
  const defenderTraits = defenderProfile?.profile || defenderProfile || {};
  const mismatch = buildMismatchSummary(traits, defenderTraits);
  const getAverage = (statKey) => {
    const values = safeLogs
      .map((log) => Number(log?.[statKey]))
      .filter((value) => !Number.isNaN(value));
    if (!values.length) {
      return null;
    }
    const sum = values.reduce((acc, value) => acc + value, 0);
    return sum / values.length;
  };
  const avgPts = getAverage("points");
  const avgReb = getAverage("rebounds");
  const avgAst = getAverage("assists");
  const livePts = player?.live?.pts ?? null;
  const liveReb = player?.live?.reb ?? null;
  const liveAst = player?.live?.ast ?? null;
  const formatDelta = (liveValue, avgValue) => {
    if (liveValue === null || liveValue === undefined) {
      return "--";
    }
    if (avgValue === null || avgValue === undefined) {
      return "--";
    }
    const delta = Number(liveValue) - Number(avgValue);
    if (Number.isNaN(delta)) {
      return "--";
    }
    const sign = delta > 0 ? "+" : "";
    return `${sign}${delta.toFixed(1)}`;
  };
  const traitsPanel = `
    <div class="stat-panel" data-stat="traits">
      <div class="traits-hero">
        <div>
          <div class="traits-hero__label">Defensor probable</div>
          <div class="traits-hero__name">${escapeHtml(defender?.player_name || "No disponible")}</div>
        </div>
        <div class="traits-hero__score">
          <span>Mismatch</span>
          <strong>${mismatch.score !== null ? mismatch.score : "--"}</strong>
          <em>${escapeHtml(mismatch.note)}</em>
        </div>
      </div>
      <div class="traits-subtitle">Juego actual vs promedio (ultimos 15)</div>
      <div class="traits-grid">
        <div class="trait-card">
          <span>PTS</span>
          <strong>${escapeHtml(formatTraitValue(livePts))}</strong>
          <small>Prom: ${escapeHtml(formatNumber(avgPts))} | Dif: ${escapeHtml(formatDelta(livePts, avgPts))}</small>
        </div>
        <div class="trait-card">
          <span>REB</span>
          <strong>${escapeHtml(formatTraitValue(liveReb))}</strong>
          <small>Prom: ${escapeHtml(formatNumber(avgReb))} | Dif: ${escapeHtml(formatDelta(liveReb, avgReb))}</small>
        </div>
        <div class="trait-card">
          <span>AST</span>
          <strong>${escapeHtml(formatTraitValue(liveAst))}</strong>
          <small>Prom: ${escapeHtml(formatNumber(avgAst))} | Dif: ${escapeHtml(formatDelta(liveAst, avgAst))}</small>
        </div>
      </div>
      <div class="traits-subtitle">Rasgos del jugador</div>
      <div class="traits-grid">
        <div class="trait-card"><span>Altura</span><strong>${escapeHtml(formatTraitValue(traits.height))}</strong></div>
        <div class="trait-card"><span>Peso</span><strong>${escapeHtml(formatTraitValue(traits.weight, " lb"))}</strong></div>
        <div class="trait-card"><span>Edad</span><strong>${escapeHtml(formatTraitValue(traits.age))}</strong></div>
        <div class="trait-card"><span>Nacimiento</span><strong>${escapeHtml(formatTraitValue(traits.birth_date))}</strong></div>
        <div class="trait-card"><span>Posición</span><strong>${escapeHtml(formatTraitValue(traits.position))}</strong></div>
        <div class="trait-card"><span>País</span><strong>${escapeHtml(formatTraitValue(traits.country))}</strong></div>
        <div class="trait-card"><span>Universidad</span><strong>${escapeHtml(formatTraitValue(traits.school))}</strong></div>
        <div class="trait-card"><span>Experiencia</span><strong>${escapeHtml(formatTraitValue(traits.experience))}</strong></div>
      </div>
      <div class="traits-subtitle">Rasgos del defensor</div>
      <div class="traits-grid">
        <div class="trait-card"><span>Altura</span><strong>${escapeHtml(formatTraitValue(defenderTraits.height))}</strong></div>
        <div class="trait-card"><span>Peso</span><strong>${escapeHtml(formatTraitValue(defenderTraits.weight, " lb"))}</strong></div>
        <div class="trait-card"><span>Edad</span><strong>${escapeHtml(formatTraitValue(defenderTraits.age))}</strong></div>
        <div class="trait-card"><span>Posición</span><strong>${escapeHtml(formatTraitValue(defenderTraits.position))}</strong></div>
      </div>
    </div>
  `;

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
      .traits-hero { display: flex; align-items: center; justify-content: space-between; gap: 16px; background: #111827; color: #fff; border-radius: 14px; padding: 16px; margin-bottom: 16px; }
      .traits-hero__label { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #cbd5f5; }
      .traits-hero__name { font-size: 18px; font-weight: 700; }
      .traits-hero__score { display: grid; gap: 4px; text-align: right; }
      .traits-hero__score span { font-size: 12px; color: #cbd5f5; text-transform: uppercase; letter-spacing: .08em; }
      .traits-hero__score strong { font-size: 22px; }
      .traits-hero__score em { font-size: 12px; color: #e2e8f0; font-style: normal; }
      .traits-subtitle { font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; margin: 14px 0 8px; }
      .traits-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
      .trait-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 14px; box-shadow: 0 10px 18px rgba(15, 23, 42, 0.08); display: grid; gap: 4px; }
      .trait-card span { font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
      .trait-card strong { font-size: 15px; color: #0f172a; }
      .trait-card small { color: #64748b; font-size: 11px; }
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
        <button class="stat-tab" data-stat="traits">Rasgos</button>
      </div>
      ${panels}
      ${traitsPanel}
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
  padding: 0 0 80px;
}

.app__content {
  display: grid;
  gap: 16px;
  margin-top: 0;
}

.app__content--playbyplay {
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  column-gap: 0;
  align-items: stretch;
}

.app__content--single {
  grid-template-columns: minmax(0, 1fr);
  align-items: stretch;
}

.app__main {
  display: grid;
  align-content: start;
}

.top-nav {
  display: flex;
  gap: 24px;
  align-items: center;
  justify-content: center;
  padding: 14px 12px;
  background: #0b0f19;
  border-radius: 0;
  width: 100%;
}

.top-nav__item {
  border: none;
  background: transparent;
  color: #e2e8f0;
  font-weight: 700;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 2px;
}

.top-nav__item--active {
  color: #ffffff;
}

.live-follow {
  display: grid;
  gap: 12px;
  padding: 8px 12px 0;
}

.live-follow__empty {
  padding: 12px;
}

.live-follow__game {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
  background: #ffffff;
  display: grid;
  gap: 8px;
}

.live-follow__card {
  display: grid;
  gap: 8px;
  cursor: pointer;
}

.live-follow__rows {
  display: grid;
  gap: 6px;
}

.live-follow__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.live-follow__row--header {
}

.live-follow__title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  color: #0f172a;
}

.live-follow__clock {
  font-size: 13px;
}

.live-follow__teams {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.live-follow__score {
  font-size: 12px;
  color: #0f172a;
  font-weight: 700;
  white-space: nowrap;
  justify-self: center;
  text-align: center;
  width: 100%;
}

.live-follow__spacer {
  width: 100%;
}


.live-follow__remove {
  border: none;
  background: transparent;
  color: #b91c1c;
  font-weight: 700;
  font-size: 11px;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  justify-self: end;
}

.playbyplay-panel {
  background: #ffffff;
  border-radius: 0;
  border: 1px solid #e5e7eb;
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.12);
  padding: 12px 14px;
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.playbyplay-panel__header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.playbyplay-panel__header h3 {
  margin: 0 0 4px;
}

.playbyplay-game-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.playbyplay-game-tab {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
}

.playbyplay-game-tab--active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}
.playbyplay-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.playbyplay-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.playbyplay-live-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #dc2626;
  box-shadow: 0 0 6px rgba(220, 38, 38, 0.7);
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

.playbyplay-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.playbyplay-tabs-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.playbyplay-updated {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

.playbyplay-tab {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}

.playbyplay-tab--active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}

.playbyplay-followed {
  display: grid;
  gap: 6px;
  margin-top: 4px;
}

.playbyplay-followed__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--center-col, 90px) minmax(0, 1fr) auto;
  column-gap: 10px;
  align-items: center;
  width: 100%;
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.playbyplay-followed__name {
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1 1 auto;
}

.playbyplay-followed__name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playbyplay-followed__live-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  display: inline-block;
  background: #e2e8f0;
  box-shadow: none;
}

.playbyplay-followed__live-dot--on {
  background: #dc2626;
  box-shadow: 0 0 6px rgba(220, 38, 38, 0.7);
}

.playbyplay-row--new {
  animation: pbpSlideIn 0.6s ease-out;
  background: #fff7ed;
}

@keyframes pbpSlideIn {
  0% {
    opacity: 0;
    transform: translateY(8px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.playbyplay-followed__line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex: 0 0 auto;
  justify-self: end;
  justify-content: flex-end;
  text-align: right;
  font-variant-numeric: tabular-nums;
  min-width: 0;
}

.playbyplay-followed__current {
  color: #475569;
  font-weight: 700;
}

.playbyplay-followed__icon {
  width: 100%;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  flex: 0 0 auto;
  justify-self: center;
}

.playbyplay-followed__icon.indicator--over {
  background: transparent;
  color: #16a34a;
}

.playbyplay-followed__icon.indicator--under {
  background: #fee2e2;
  color: #dc2626;
}

.playbyplay-list {
  flex: 1;
  overflow-y: auto;
  border-radius: 0;
  border: 1px solid #e5e7eb;
}

.playbyplay-row--followed-a { background: #fef9c3; }
.playbyplay-row--followed-b { background: #dcfce7; }
.playbyplay-row--followed-c { background: #dbeafe; }
.playbyplay-row--followed-d { background: #fae8ff; }
.playbyplay-row--followed-e { background: #ffe4e6; }
.playbyplay-row--followed-f { background: #e0f2fe; }

.playbyplay-row--followed-a .playbyplay-desc,
.playbyplay-row--followed-b .playbyplay-desc,
.playbyplay-row--followed-c .playbyplay-desc,
.playbyplay-row--followed-d .playbyplay-desc,
.playbyplay-row--followed-e .playbyplay-desc,
.playbyplay-row--followed-f .playbyplay-desc {
  font-weight: 700;
}

.follow-modal__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  z-index: 50;
}

.follow-modal {
  width: min(420px, 92vw);
  background: #ffffff;
  border-radius: 16px;
  padding: 16px;
  display: grid;
  gap: 12px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.3);
}

.follow-modal__header h3 {
  margin: 0 0 4px;
}

.follow-modal__body {
  display: grid;
  gap: 10px;
}

.follow-modal__options {
  display: grid;
  gap: 8px;
}

.follow-modal__section {
  display: grid;
  gap: 8px;
}

.follow-modal__toggle {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}

.follow-modal__toggle-button {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px 12px;
  background: #ffffff;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
}

.follow-modal__toggle-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.follow-modal__toggle-button--active {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
}

.follow-modal__input input {
  width: 100%;
  height: 40px;
  border: 1px solid #cbd5f5;
  border-radius: 10px;
  padding: 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.follow-modal__footer {
  display: flex;
  gap: 10px;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
}

.follow-modal__footer .ghost-button {
  flex: 1 1 30%;
  border-radius: 999px;
  padding: 10px 12px;
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 0.02em;
}

.follow-modal__footer .ghost-button--danger {
  background: #fee2e2;
  border-color: #fecaca;
  color: #b91c1c;
}

.follow-modal__footer .ghost-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.follow-modal__option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
  background: #f8fafc;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
}

.follow-modal__option--active {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
}

.follow-modal__option-label {
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #334155;
}

.follow-modal__option-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.follow-modal__option-icon {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
}

.follow-modal__option-icon.indicator--over {
  background: #dcfce7;
  color: #16a34a;
}

.follow-modal__option-icon.indicator--under {
  background: #fee2e2;
  color: #dc2626;
}

.follow-modal__footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.ghost-button--danger {
  background: #fee2e2;
  border-color: #fecaca;
  color: #b91c1c;
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
