<template>
  <section v-if="game" class="lineup-panel">
    <div v-if="!isFinal && isLoading" class="lineup-panel__state muted">Cargando lineup...</div>
    <div v-else-if="!isFinal && error" class="lineup-panel__state error">{{ error }}</div>
    <div v-else-if="!isFinal && !lineup" class="lineup-panel__state muted">No hay lineup disponible.</div>

    <div v-else-if="!isFinal" class="lineup-panel__content">
      <div v-if="teams.length > 1" class="team-tabs">
        <button
          v-for="team in teams"
          :key="team.key"
          type="button"
          class="team-tab"
          :class="{ 'team-tab--active': team.key === selectedTeamKey }"
          @click="selectedTeamKey = team.key"
        >
          <img v-if="team.logo" :src="team.logo" :alt="team.name" />
          <span>{{ team.key }}</span>
        </button>
      </div>
      <article v-if="selectedTeam" class="team-block">
        <div class="player-grid">
          <div
            v-for="player in selectedTeam.players"
            :key="player.id"
            class="player-card"
            :class="[
              player.probabilityClass,
              { 'player-card--odds-flash': player.oddsFlash, 'player-card--disabled': player.isDisabled }
            ]"
          >
            <div class="player-card__top">
              <span class="position-chip">{{ player.position }}</span>
              <span
                class="live-indicator"
                :class="{ 'live-indicator--on': player.isOnCourt }"
                :title="player.isOnCourt ? 'EN CANCHA' : 'EN BANCA'"
                aria-hidden="true"
              ></span>
            </div>

            <p v-if="player.jerseyNumber" class="player-card__number">#{{ player.jerseyNumber }}</p>

            <div class="player-card__avatar">
              <img v-if="player.photo" :src="player.photo" :alt="player.name" />
              <div v-else class="avatar-fallback"></div>
            </div>

            <p class="player-card__name">{{ player.name }}</p>
            <p v-if="player.probabilityLabel" class="player-card__prob">
              {{ player.probabilityLabel }}
            </p>

            <div class="player-card__stats">
              <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'points' }">
                <span class="stat-label">PTS</span>
                <span class="stat-indicator" :class="player.pointsIndicator.className">
                  {{ player.pointsIndicator.symbol }}
                </span>
                <span class="stat-value">{{ formatLine(player.pointsLine) }}</span>
              </div>
              <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'rebounds' }">
                <span class="stat-label">REB</span>
                <span class="stat-indicator" :class="player.reboundsIndicator.className">
                  {{ player.reboundsIndicator.symbol }}
                </span>
                <span class="stat-value">{{ formatLine(player.reboundsLine) }}</span>
              </div>
              <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'assists' }">
                <span class="stat-label">AST</span>
                <span class="stat-indicator" :class="player.assistsIndicator.className">
                  {{ player.assistsIndicator.symbol }}
                </span>
                <span class="stat-value">{{ formatLine(player.assistsLine) }}</span>
              </div>
            </div>

            <div class="stat-divider" v-if="player.live"></div>
            <div class="player-card__stats player-card__stats--live" v-if="player.live">
              <div class="stat-row">
                <span class="stat-label">PTS</span>
                <span class="stat-indicator stat-indicator--flat">—</span>
                <span class="stat-value">{{ formatLiveValue(player.live.pts) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">REB</span>
                <span class="stat-indicator stat-indicator--flat">—</span>
                <span class="stat-value">{{ formatLiveValue(player.live.reb) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">AST</span>
                <span class="stat-indicator stat-indicator--flat">—</span>
                <span class="stat-value">{{ formatLiveValue(player.live.ast) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">PF</span>
                <span class="stat-indicator stat-indicator--flat">—</span>
                <span class="stat-value">{{ formatLiveValue(player.live.pf) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">MIN</span>
                <span class="stat-indicator stat-indicator--flat">—</span>
                <span class="stat-value">{{ formatLiveMinutes(player.live.min) }}</span>
              </div>
            </div>

            <div class="subs-row" v-if="player.subStats || player.live">
              <span>SUBS IN {{ player.subStats?.subsIn || 0 }} OUT {{ player.subStats?.subsOut || 0 }}</span>
              <span v-if="player.isOnCourt">FLOOR {{ formatFloorTime(player.subStats, player.isOnCourt, player.liveMinutes) }}</span>
              <span v-else-if="player.benchTime">BANCA {{ player.benchTime }}</span>
              <span v-if="player.subOutProb !== null && player.subOutProb !== undefined">
                OUT SOON {{ player.subOutProb }}%
              </span>
            </div>

            <div v-if="player.valueSignal" class="value-pill" :class="player.valueSignal.className">
              {{ player.valueSignal.label }}
            </div>

            <div class="player-card__actions">
              <button
                class="ghost-button ghost-button--follow"
                :class="{ 'ghost-button--active': isFollowed(player) }"
                type="button"
                :disabled="player.isDisabled"
                @click="handleFollowRequest(player)"
              >
                {{ isFollowed(player) ? "Siguiendo" : "Follow" }}
              </button>
              <button class="ghost-button" type="button" :disabled="player.isDisabled" @click="handleShowLogs(player)">
                Ver Ultimos Juegos
              </button>
              <span class="status-pill" :class="{ 'status-pill--starter': player.isStarter }">
                {{ player.isStarter ? "STARTER" : "BENCH" }}
              </span>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  game: {
    type: Object,
    default: null
  },
  lineup: {
    type: Object,
    default: null
  },
  liveStats: {
    type: Object,
    default: () => ({})
  },
  subsStats: {
    type: Object,
    default: () => ({})
  },
  minutesAvg: {
    type: Object,
    default: () => ({})
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ""
  },
  oddsRequested: {
    type: Boolean,
    default: false
  },
  timeoutLabel: {
    type: String,
    default: ""
  },
  followedPlayers: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(["show-logs", "follow-request"]);

const followedIds = computed(() => new Set(
  (props.followedPlayers || []).map((player) => String(player?.playerId || ""))
));

const isFollowed = (player) => followedIds.value.has(String(player?.playerId || ""));

const handleFollowRequest = (player) => {
  emit("follow-request", player);
};

const hasOddsLines = (player) => {
  if (!player) {
    return false;
  }
  if (player.has_current_odds !== null && player.has_current_odds !== undefined) {
    return Boolean(player.has_current_odds);
  }
  const values = [player.points_line, player.rebounds_line, player.assists_line];
  return values.some((value) => value !== null && value !== undefined && !Number.isNaN(value));
};

const teamHasAnyOdds = (teamLineup) => {
  if (!teamLineup) {
    return false;
  }
  const starters = ["PG", "SG", "SF", "PF", "C"]
    .map((position) => teamLineup[position])
    .filter(Boolean);
  const bench = Array.isArray(teamLineup.BENCH) ? teamLineup.BENCH : [];
  return [...starters, ...bench].some((player) => hasOddsLines(player));
};

const formatPlayers = (teamLineup, benchLabel, teamKey) => {
  if (!teamLineup) {
    return [];
  }
  const shouldFilterOdds = props.oddsRequested || teamHasAnyOdds(teamLineup);
  const starters = ["PG", "SG", "SF", "PF", "C"]
    .map((position) => {
      const player = teamLineup[position];
      if (!player) {
        return null;
      }
      const hasOdds = hasOddsLines(player);
      const hasHistory = Boolean(player.over_under_history?.total_games);
      if (shouldFilterOdds && !hasOdds && !hasHistory) {
        return null;
      }
      const probability = getCardProbability(player);
      const live = getLiveStats(player.player_id, player.player_name, teamKey);
      const subStats = getSubStats(player.player_id, player.player_name);
      const isOnCourt = isOnCourtLive(live);
      const liveMinutes = live ? parseDurationMinutes(live.min) : 0;
      const benchTime = formatBenchTime(subStats, isOnCourt, liveMinutes);
      const benchSeconds = getBenchSeconds(subStats, isOnCourt, liveMinutes);
      const floorSeconds = getFloorSeconds(subStats, isOnCourt, liveMinutes);
      const avgMinutes = props.minutesAvg?.[player.player_id] || null;
      const subOutProb = getSubOutProbability(avgMinutes, liveMinutes);
      const valueSignal = getValueSignal(
        player,
        isOnCourt,
        subOutProb,
        floorSeconds,
        benchSeconds,
        liveMinutes,
        avgMinutes
      );
      const isDisabled = shouldFilterOdds && !hasOdds;
      return {
        id: `${position}-${player.player_id}`,
        playerId: player.player_id,
        name: player.player_name,
        photo: player.player_photo_url,
        jerseyNumber: player.jersey_number || player.jerseyNumber || player.jersey || player.number || "",
        position,
        status: player.player_status || "",
        confirmed: Boolean(player.confirmed),
        hasGameLog: Boolean(player.over_under_history?.total_games),
        isStarter: position !== "BENCH" && player.player_status !== "BENCH",
        pointsLine: player.points_line,
        reboundsLine: player.rebounds_line,
        assistsLine: player.assists_line,
        bestStat: getBestStatType(player),
        probabilityClass: probability.className,
        probabilityLabel: probability.label,
        probabilityRank: probability.rank,
        probabilityPercent: probability.probabilityPercent,
        pointsIndicator: getIndicator(player.points_line, getStatProbability(player.over_under_history, "points")),
        reboundsIndicator: getIndicator(player.rebounds_line, getStatProbability(player.over_under_history, "rebounds")),
        assistsIndicator: getIndicator(player.assists_line, getStatProbability(player.over_under_history, "assists")),
        oddsFlash: Boolean(player.oddsFlash),
        isDisabled,
        teamKey,
        live,
        isOnCourt,
        subStats,
        benchTime,
        liveMinutes,
        avgMinutes,
        subOutProb,
        valueSignal
      };
    })
    .filter(Boolean);

  const bench = Array.isArray(teamLineup.BENCH)
    ? teamLineup.BENCH
        .filter((player) => {
          if (!player) {
            return false;
          }
          const hasOdds = hasOddsLines(player);
          const hasHistory = Boolean(player.over_under_history?.total_games);
          return !shouldFilterOdds || hasOdds || hasHistory;
        })
        .map((player) => {
          const hasOdds = hasOddsLines(player);
          const isDisabled = shouldFilterOdds && !hasOdds;
          const probability = getCardProbability(player);
          const live = getLiveStats(player.player_id, player.player_name, teamKey);
          const subStats = getSubStats(player.player_id, player.player_name);
          const isOnCourt = isOnCourtLive(live);
          const liveMinutes = live ? parseDurationMinutes(live.min) : 0;
          const benchTime = formatBenchTime(subStats, isOnCourt, liveMinutes);
          const benchSeconds = getBenchSeconds(subStats, isOnCourt, liveMinutes);
          const floorSeconds = getFloorSeconds(subStats, isOnCourt, liveMinutes);
          const avgMinutes = props.minutesAvg?.[player.player_id] || null;
          const subOutProb = getSubOutProbability(avgMinutes, liveMinutes);
          const valueSignal = getValueSignal(
            player,
            isOnCourt,
            subOutProb,
            floorSeconds,
            benchSeconds,
            liveMinutes,
            avgMinutes
          );
          return {
          id: `BENCH-${player.player_id}`,
          playerId: player.player_id,
          name: player.player_name,
          photo: player.player_photo_url,
          jerseyNumber: player.jersey_number || player.jerseyNumber || player.jersey || player.number || "",
          position: benchLabel,
          status: player.player_status || "BENCH",
          confirmed: Boolean(player.confirmed),
          hasGameLog: Boolean(player.over_under_history?.total_games),
          isStarter: false,
          pointsLine: player.points_line,
          reboundsLine: player.rebounds_line,
          assistsLine: player.assists_line,
          bestStat: getBestStatType(player),
          probabilityClass: probability.className,
          probabilityLabel: probability.label,
          probabilityRank: probability.rank,
          probabilityPercent: probability.probabilityPercent,
          pointsIndicator: getIndicator(player.points_line, getStatProbability(player.over_under_history, "points")),
          reboundsIndicator: getIndicator(player.rebounds_line, getStatProbability(player.over_under_history, "rebounds")),
          assistsIndicator: getIndicator(player.assists_line, getStatProbability(player.over_under_history, "assists")),
          oddsFlash: Boolean(player.oddsFlash),
          isDisabled,
          teamKey,
          live,
          isOnCourt,
          subStats,
          benchTime,
          liveMinutes,
          avgMinutes,
          subOutProb,
          valueSignal
        };
        })
    : [];

  return [...starters, ...bench].sort((a, b) => {
    if (a.probabilityRank !== b.probabilityRank) {
      return a.probabilityRank - b.probabilityRank;
    }
    if (a.probabilityPercent !== b.probabilityPercent) {
      return b.probabilityPercent - a.probabilityPercent;
    }
    return a.name.localeCompare(b.name);
  });
};

const teams = computed(() => {
  if (!props.lineup?.lineups) {
    return [];
  }
  const lineup = props.lineup;
  const awayKey = lineup.away_team;
  const homeKey = lineup.home_team;
  return [
    {
      key: awayKey,
      name: lineup.away_team_name || awayKey,
      logo: lineup.away_team_logo_url,
      players: formatPlayers(lineup.lineups[awayKey], "BENCH", awayKey)
    },
    {
      key: homeKey,
      name: lineup.home_team_name || homeKey,
      logo: lineup.home_team_logo_url,
      players: formatPlayers(lineup.lineups[homeKey], "BENCH", homeKey)
    }
  ].filter((team) => team.key);
});

const selectedTeamKey = ref("");

const selectedTeam = computed(() => {
  if (!teams.value.length) {
    return null;
  }
  return teams.value.find((team) => team.key === selectedTeamKey.value) || teams.value[0];
});

watch(teams, (nextTeams) => {
  if (!nextTeams.length) {
    selectedTeamKey.value = "";
    return;
  }
  const exists = nextTeams.some((team) => team.key === selectedTeamKey.value);
  if (!exists) {
    selectedTeamKey.value = nextTeams[0].key;
  }
}, { immediate: true });

const formatLine = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return Number(value).toFixed(1);
};

const handleShowLogs = (player) => {
  emit("show-logs", player);
};

const formatLiveValue = (value) => {
  if (value === null || value === undefined) {
    return "";
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return "";
  }
  return numeric.toString();
};

const parseDurationMinutes = (value) => {
  if (!value) {
    return 0;
  }
  if (typeof value === "number") {
    return value;
  }
  const numeric = Number(value);
  if (!Number.isNaN(numeric)) {
    return numeric;
  }
  if (String(value).includes(":")) {
    const [mins, secs] = String(value).split(":").map((part) => Number(part));
    if (!Number.isNaN(mins) && !Number.isNaN(secs)) {
      return mins + secs / 60;
    }
  }
  const match = String(value).match(/PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?/i);
  if (match) {
    const mins = Number(match[1] || 0);
    const secs = Number(match[2] || 0);
    return mins + secs / 60;
  }
  return 0;
};

const getSubOutProbability = (avgMinutes, liveMinutes) => {
  if (!avgMinutes || !liveMinutes) {
    return null;
  }
  const ratio = liveMinutes / avgMinutes;
  if (!Number.isFinite(ratio)) {
    return null;
  }
  if (ratio >= 1.1) {
    return Math.min(100, Math.round(85 + ((ratio - 1.1) / 0.3) * 15));
  }
  if (ratio >= 0.9) {
    return Math.round(60 + ((ratio - 0.9) / 0.2) * 25);
  }
  if (ratio >= 0.7) {
    return Math.round(35 + ((ratio - 0.7) / 0.2) * 25);
  }
  return Math.round(15 + (ratio / 0.7) * 20);
};

const formatLiveMinutes = (value) => {
  const minutes = parseDurationMinutes(value);
  if (!minutes) {
    return "";
  }
  const whole = Math.floor(minutes);
  const secs = Math.floor((minutes - whole) * 60);
  return `${whole}:${secs.toString().padStart(2, "0")}`;
};

const normalizeFlag = (value) => String(value ?? "").trim().toLowerCase();

const isOnCourtLive = (live) => {
  if (!live) {
    return false;
  }
  const oncourtFlag = normalizeFlag(live.oncourt);
  if (oncourtFlag) {
    return oncourtFlag === "1" || oncourtFlag === "true" || oncourtFlag === "yes";
  }
  const statusText = normalizeFlag(live.status);
  if (statusText) {
    if (statusText.includes("inactive") || statusText === "bench") {
      return false;
    }
    if (statusText.includes("active")) {
      return true;
    }
  }
  const playedFlag = normalizeFlag(live.played);
  if (playedFlag) {
    return playedFlag === "1" || playedFlag === "true";
  }
  return false;
};

const formatLiveStatus = (status, minutes, oncourt, played) => {
  const oncourtFlag = normalizeFlag(oncourt);
  if (oncourtFlag) {
    return oncourtFlag === "1" || oncourtFlag === "true" || oncourtFlag === "yes"
      ? "EN CANCHA"
      : "EN BANCA";
  }
  const statusText = normalizeFlag(status);
  if (statusText) {
    if (statusText.includes("inactive") || statusText === "bench") {
      return "EN BANCA";
    }
    if (statusText.includes("active")) {
      return "EN CANCHA";
    }
  }
  const playedFlag = normalizeFlag(played);
  if (playedFlag) {
    return playedFlag === "1" || playedFlag === "true" ? "EN CANCHA" : "EN BANCA";
  }
  return "EN BANCA";
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

const getLiveStats = (playerId, playerName, teamKey) => {
  const normalizedTeam = normalizeTeamTricode(teamKey);
  const teamBucket = normalizedTeam ? props.liveStats?.byTeam?.[normalizedTeam] : null;
  const stats = teamBucket?.byId?.[playerId] || props.liveStats?.byId?.[playerId];
  if (stats) {
    return stats;
  }
  const key = normalizeName(playerName);
  if (!key) {
    return null;
  }
  return teamBucket?.byName?.[key] || props.liveStats?.byName?.[key] || null;
};

const getSubStats = (playerId, playerName) => {
  const stats = props.subsStats?.byId?.[playerId];
  if (stats) {
    return stats;
  }
  const key = normalizeName(playerName);
  if (!key) {
    return null;
  }
  return props.subsStats?.byName?.[key] || null;
};

const parseGameClockSeconds = (clock) => {
  if (!clock) {
    return null;
  }
  const match = /PT(\d+)M(\d+)\.(\d+)S/.exec(String(clock));
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

const getGameElapsedSeconds = () => {
  const period = Number(props.game?.gamePeriod);
  if (!period) {
    return null;
  }
  const remaining = parseGameClockSeconds(props.game?.gameClock);
  if (remaining === null) {
    return null;
  }
  const periodLength = period > 4 ? 300 : 720;
  const previousReg = Math.min(period - 1, 4);
  const previousOt = Math.max(period - 5, 0);
  const previousSeconds = previousReg * 720 + previousOt * 300;
  const elapsedInPeriod = Math.max(0, periodLength - remaining);
  return previousSeconds + elapsedInPeriod;
};

const formatBenchTime = (subStats, isOnCourt, liveMinutes) => {
  if (isOnCourt) {
    return "";
  }
  const currentElapsed = props.subsStats?.currentElapsed;
  if (currentElapsed !== null && currentElapsed !== undefined && subStats?.lastOutElapsed) {
    const elapsed = Math.max(0, currentElapsed - subStats.lastOutElapsed);
    const mins = Math.floor(elapsed / 60);
    const secs = Math.floor(elapsed % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }
  const gameElapsed = getGameElapsedSeconds();
  if (gameElapsed === null || !liveMinutes) {
    return "";
  }
  const benchSeconds = Math.max(0, gameElapsed - liveMinutes * 60);
  const mins = Math.floor(benchSeconds / 60);
  const secs = Math.floor(benchSeconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const formatFloorTime = (subStats, isOnCourt, liveMinutes) => {
  if (!isOnCourt) {
    return "";
  }
  const currentElapsed = props.subsStats?.currentElapsed;
  if (currentElapsed !== null && currentElapsed !== undefined && subStats?.lastInElapsed) {
    const elapsed = Math.max(0, currentElapsed - subStats.lastInElapsed);
    const mins = Math.floor(elapsed / 60);
    const secs = Math.floor(elapsed % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }
  const gameElapsed = getGameElapsedSeconds();
  if (gameElapsed !== null && subStats?.lastInElapsed) {
    const elapsed = Math.max(0, gameElapsed - subStats.lastInElapsed);
    const mins = Math.floor(elapsed / 60);
    const secs = Math.floor(elapsed % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }
  if (!liveMinutes) {
    return "";
  }
  return formatLiveMinutes(liveMinutes);
};

const getBenchSeconds = (subStats, isOnCourt, liveMinutes) => {
  if (isOnCourt) {
    return null;
  }
  const currentElapsed = props.subsStats?.currentElapsed;
  if (currentElapsed !== null && currentElapsed !== undefined && subStats?.lastOutElapsed) {
    return Math.max(0, currentElapsed - subStats.lastOutElapsed);
  }
  const gameElapsed = getGameElapsedSeconds();
  if (gameElapsed === null || !liveMinutes) {
    return null;
  }
  return Math.max(0, gameElapsed - liveMinutes * 60);
};

const getFloorSeconds = (subStats, isOnCourt, liveMinutes) => {
  if (!isOnCourt) {
    return null;
  }
  const currentElapsed = props.subsStats?.currentElapsed;
  if (currentElapsed !== null && currentElapsed !== undefined && subStats?.lastInElapsed) {
    return Math.max(0, currentElapsed - subStats.lastInElapsed);
  }
  if (!liveMinutes) {
    return null;
  }
  return Math.max(0, liveMinutes * 60);
};

const getValueSignal = (player, isOnCourt, subOutProb, floorSeconds, benchSeconds, liveMinutes, avgMinutes) => {
  const bestType = getBestStatType(player);
  if (!bestType) {
    return null;
  }
  const prob = getStatProbability(player.over_under_history, bestType);
  if (!prob || prob.percent < 70) {
    return null;
  }
  const hasHighSubOut = subOutProb !== null && subOutProb !== undefined && subOutProb >= 60;
  const hasMinutesSignal = avgMinutes
    ? liveMinutes >= avgMinutes * 0.9
    : floorSeconds !== null && floorSeconds >= 600;
  if (isOnCourt && prob.side === "UNDER" && floorSeconds !== null && floorSeconds >= 360 && (hasHighSubOut || hasMinutesSignal)) {
    return { label: "VALOR UNDER", className: "value-pill--under" };
  }
  if (!isOnCourt && benchSeconds !== null && benchSeconds >= 120 && prob.side === "OVER") {
    return { label: "VALOR OVER", className: "value-pill--over" };
  }
  return null;
};

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

const getIndicator = (line, probability) => {
  if (line === null || line === undefined || Number.isNaN(line)) {
    return { symbol: "", className: "" };
  }
  if (!probability || probability.percent < 60) {
    return { symbol: "—", className: "stat-indicator--flat" };
  }
  if (probability.side === "OVER") {
    return { symbol: "▲", className: "stat-indicator--up" };
  }
  return { symbol: "▼", className: "stat-indicator--down" };
};

const getBestStatType = (player) => {
  if (!player) {
    return null;
  }
  const history = player.over_under_history;
  const candidates = [];
  if (player.points_line != null) {
    const prob = getStatProbability(history, "points");
    if (prob) {
      candidates.push(prob);
    }
  }
  if (player.rebounds_line != null) {
    const prob = getStatProbability(history, "rebounds");
    if (prob) {
      candidates.push(prob);
    }
  }
  if (player.assists_line != null) {
    const prob = getStatProbability(history, "assists");
    if (prob) {
      candidates.push(prob);
    }
  }
  if (!candidates.length) {
    return null;
  }
  const best = candidates.sort((a, b) => b.percent - a.percent)[0];
  return best?.type || null;
};

const getCardProbability = (player) => {
  const history = player.over_under_history;
  const candidates = [];
  if (player.points_line != null) {
    const prob = getStatProbability(history, "points");
    if (prob) {
      candidates.push(prob);
    }
  }
  if (player.rebounds_line != null) {
    const prob = getStatProbability(history, "rebounds");
    if (prob) {
      candidates.push(prob);
    }
  }
  if (player.assists_line != null) {
    const prob = getStatProbability(history, "assists");
    if (prob) {
      candidates.push(prob);
    }
  }
  if (!candidates.length) {
    return { className: "", label: "", rank: 5, probabilityPercent: 0 };
  }
  const best = candidates.sort((a, b) => b.percent - a.percent)[0];
  let className = "";
  let rank = 5;
  if (best.percent >= 90) {
    className = "player-card--red";
    rank = 1;
  } else if (best.percent >= 80) {
    className = "player-card--platinum";
    rank = 2;
  }
  const typeLabel = best.type === "points" ? "PTS" : best.type === "rebounds" ? "REB" : "AST";
  return {
    className,
    label: className ? `${typeLabel} ${best.side} ${best.percent.toFixed(0)}%` : "",
    rank,
    probabilityPercent: best.percent
  };
};

const awayTeam = computed(() => ({
  name: props.lineup?.away_team_name || props.game?.awayName || "Away",
  logo: props.lineup?.away_team_logo_url || props.game?.awayLogo || ""
}));

const homeTeam = computed(() => ({
  name: props.lineup?.home_team_name || props.game?.homeName || "Home",
  logo: props.lineup?.home_team_logo_url || props.game?.homeLogo || ""
}));

const awayRecord = computed(() => props.game?.awayRecord || "");
const homeRecord = computed(() => props.game?.homeRecord || "");

const statusText = computed(() => (props.game?.gameStatusText || props.lineup?.status || "").toString());
const isFinal = computed(() => {
  const statusCode = Number(props.game?.gameStatus);
  if (!Number.isNaN(statusCode) && statusCode === 3) {
    return true;
  }
  return statusText.value.toLowerCase().includes("final");
});

const startDate = computed(() => {
  if (props.game?.gameTimeUTC) {
    const date = new Date(props.game.gameTimeUTC);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  return null;
});

const hasStarted = computed(() => {
  if (props.game?.gameStatus != null) {
    return Number(props.game.gameStatus) >= 2;
  }
  if (startDate.value) {
    return Date.now() >= startDate.value.getTime();
  }
  return false;
});

const formatClock = (clock) => {
  if (!clock) {
    return "";
  }
  const match = /PT(\d+)M(\d+)\.(\d+)S/.exec(clock);
  if (!match) {
    return "";
  }
  const minutes = String(match[1]).padStart(2, "0");
  const seconds = String(match[2]).padStart(2, "0");
  return `${minutes}:${seconds}`;
};

const headerTime = computed(() => {
  if (!hasStarted.value) {
    return props.game?.time || "";
  }
  if (statusText.value) {
    return statusText.value;
  }
  const period = props.game?.gamePeriod || 1;
  const clock = formatClock(props.game?.gameClock) || "00:00";
  return `Q${period} ${clock}`;
});

const homeScore = computed(() => props.game?.homeScore ?? props.lineup?.home_score ?? 0);
const awayScore = computed(() => props.game?.awayScore ?? props.lineup?.away_score ?? 0);

const showScore = computed(() => hasStarted.value);
</script>

<style scoped>
.lineup-panel {
  width: 100%;
  margin: 0 auto;
  padding: 0 12px 16px;
}


.lineup-panel__state {
  margin-top: 12px;
  padding: 0 12px;
}

.lineup-panel__content {
  display: grid;
  gap: 12px;
  margin-top: 10px;
  padding: 0 12px;
}

.value-legend {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.team-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
}

.team-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 800;
  color: #0f172a;
  cursor: pointer;
  width: 100%;
}

.team-tab img {
  width: 18px;
  height: 18px;
  object-fit: contain;
}

.team-tab--active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}

.legend-item {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
}

.legend-item--yellow {
  background: #fff7ed;
  color: #b45309;
}

.legend-item--green {
  background: #ecfdf3;
  color: #15803d;
}

.legend-item--platinum {
  background: #eef2ff;
  color: #4338ca;
}

.legend-item--red {
  background: #fef2f2;
  color: #b91c1c;
}

.team-block {
  display: grid;
  gap: 12px;
}

.team-block__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.team-block__abbr {
  font-weight: 700;
  color: #64748b;
}

.team {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
}

.team img {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.player-grid {
  display: flex;
  flex-wrap: nowrap;
  gap: 12px;
  justify-content: center;
  overflow-x: auto;
  padding-bottom: 6px;
}

.player-card {
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 12px 14px 14px;
  display: grid;
  gap: 10px;
  background: #ffffff;
  position: relative;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
  width: 220px;
  min-height: 360px;
}

.player-card--odds-flash {
  animation: odds-flash 3.5s ease-out;
}

@keyframes odds-flash {
  0% {
    box-shadow:
      0 0 0 rgba(16, 185, 129, 0),
      0 0 0 rgba(16, 185, 129, 0);
  }
  15% {
    box-shadow:
      0 0 18px rgba(16, 185, 129, 0.55),
      0 0 36px rgba(16, 185, 129, 0.35);
  }
  100% {
    box-shadow:
      0 0 0 rgba(16, 185, 129, 0),
      0 0 0 rgba(16, 185, 129, 0);
  }
}

.player-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.12);
}

.player-card--yellow {
  border-color: #f59e0b;
  box-shadow: 0 10px 20px rgba(245, 158, 11, 0.2);
}

.player-card--green {
  border-color: #22c55e;
  box-shadow: 0 10px 20px rgba(34, 197, 94, 0.2);
}

.player-card--platinum {
  border-color: #6366f1;
  box-shadow: 0 10px 20px rgba(99, 102, 241, 0.2);
}

.player-card--red {
  border-color: #ef4444;
  box-shadow: 0 10px 20px rgba(239, 68, 68, 0.2);
}

.player-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.player-card__number {
  text-align: center;
  font-weight: 800;
  font-size: 13px;
  color: #1f2937;
  letter-spacing: 0.08em;
}

.position-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #1d4ed8;
  background: #e0e7ff;
}

.live-indicator {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #cbd5f5;
  box-shadow: inset 0 0 0 2px #e2e8f0;
}

.live-indicator--on {
  background: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
}

.player-card__avatar {
  display: grid;
  place-items: center;
}

.player-card__avatar img {
  width: 64px;
  height: 64px;
  border-radius: 999px;
  object-fit: cover;
  border: 3px solid #c7d2fe;
  box-shadow: 0 6px 12px rgba(79, 70, 229, 0.2);
}

.avatar-fallback {
  width: 64px;
  height: 64px;
  border-radius: 999px;
  background: #e2e8f0;
}

.player-card__name {
  margin: 2px 0 0;
  font-weight: 700;
  text-align: center;
}

.player-card__prob {
  margin: 0;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.player-card__stats {
  display: grid;
  gap: 6px;
}

.stat-divider {
  height: 1px;
  width: 100%;
  background: #e5e7eb;
  margin: 4px 0;
}

.player-card__stats--live .stat-row {
  background: #f8fafc;
  color: #475569;
}

.stat-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  background: #f8fafc;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  border: 1px solid transparent;
}

.stat-row--best {
  background: #dcfce7;
  border-color: #22c55e;
  color: #14532d;
}

.stat-row--best .stat-label {
  color: #15803d;
}

.stat-row--best .stat-value {
  color: #14532d;
}

.stat-label {
  color: #94a3b8;
}

.stat-value {
  color: #0f172a;
  text-align: right;
}

.stat-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  font-size: 12px;
  font-weight: 900;
  color: #94a3b8;
}

.stat-indicator--up {
  color: #16a34a;
}

.stat-indicator--down {
  color: #dc2626;
}

.stat-indicator--flat {
  color: #64748b;
}

.subs-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 10px;
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
}

.value-pill {
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid transparent;
  animation: valueFloat 2.2s ease-in-out infinite;
}

.value-pill--under {
  color: #991b1b;
  background: #fee2e2;
  border-color: #fecaca;
}

.value-pill--over {
  color: #1d4ed8;
  background: #e0e7ff;
  border-color: #c7d2fe;
}

@keyframes valueFloat {
  0% { transform: translateY(0); box-shadow: 0 0 0 rgba(0, 0, 0, 0); }
  50% { transform: translateY(-3px); box-shadow: 0 10px 18px rgba(15, 23, 42, 0.18); }
  100% { transform: translateY(0); box-shadow: 0 0 0 rgba(0, 0, 0, 0); }
}

.player-card__actions {
  display: grid;
  gap: 8px;
  margin-top: 4px;
}

.player-card--disabled {
  opacity: 0.55;
  filter: grayscale(0.25);
  pointer-events: none;
}

.ghost-button {
  width: 100%;
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #f1f5ff;
  color: #1e1b4b;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.ghost-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(79, 70, 229, 0.18);
}

.ghost-button--follow {
  background: #f8fafc;
}

.ghost-button--follow.ghost-button--active {
  background: #ecfdf3;
  border-color: #16a34a;
  color: #166534;
}

.status-pill {
  width: 100%;
  padding: 8px 10px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
  text-align: center;
}

.status-pill--starter {
  background: #22c55e;
  color: #ffffff;
}

.muted {
  color: #6b7280;
}

.error {
  color: #b91c1c;
}
</style>
