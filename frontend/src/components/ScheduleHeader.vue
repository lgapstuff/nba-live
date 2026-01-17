<template>
  <section class="schedule">
    <div class="schedule-status">
      <p v-if="isLoading" class="muted">Cargando juegos...</p>
      <p v-else-if="error" class="error">{{ error }}</p>
      <p v-else-if="games.length === 0" class="muted">No hay juegos hoy.</p>
    </div>

    <div class="schedule-row" v-if="games.length">
      <div class="schedule-date" aria-hidden="true">
        <span class="schedule-date__weekday">{{ dateLabel.weekday }}</span>
        <span class="schedule-date__day">{{ dateLabel.day }}</span>
        <span class="schedule-date__month">{{ dateLabel.month }}</span>
      </div>
      <div class="schedule-strip">
        <div class="schedule-strip__list">
          <article
            v-for="game in games"
            :key="game.gameId"
            class="schedule-card"
            :class="{
              'schedule-card--active': game.gameId === selectedGameId,
              'schedule-card--loading': game.gameId === loadingGameId
            }"
            role="button"
            tabindex="0"
            @click="handleSelect(game)"
            @keydown.enter.prevent="handleSelect(game)"
          >
            <div class="schedule-card__header">
              <span class="badge" v-if="game.label">{{ game.label }}</span>
              <span class="time" v-if="game.time">{{ game.time }}</span>
            </div>
            <div class="schedule-card__teams">
              <div class="team-row">
                <div class="team">
                  <img v-if="game.awayLogo" :src="game.awayLogo" :alt="game.awayName" />
                  <span>{{ game.awayName }}</span>
                </div>
                <span class="record">{{ game.awayRecord }}</span>
              </div>
              <div class="team-row">
                <div class="team">
                  <img v-if="game.homeLogo" :src="game.homeLogo" :alt="game.homeName" />
                  <span>{{ game.homeName }}</span>
                </div>
                <span class="record">{{ game.homeRecord }}</span>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { fetchCdnScoreboard } from "../api/endpoints";

const props = defineProps({
  selectedGameId: {
    type: String,
    default: ""
  },
  loadingGameId: {
    type: String,
    default: ""
  }
});

const emit = defineEmits(["select", "loaded"]);

const games = ref([]);
const isLoading = ref(true);
const error = ref(null);
const dateLabel = ref({ weekday: "", day: "", month: "" });

const formatRecord = (wins, losses) => {
  if (wins === undefined || losses === undefined) {
    return "";
  }
  return `${wins}-${losses}`;
};

const getTeamLogo = (teamId) => {
  if (!teamId) {
    return "";
  }
  return `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;
};

const formatScoreboardDate = (value) => {
  if (!value) {
    return { weekday: "", day: "", month: "" };
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { weekday: "", day: "", month: "" };
  }
  return {
    weekday: date.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase(),
    day: date.toLocaleDateString("en-US", { day: "2-digit" }),
    month: date.toLocaleDateString("en-US", { month: "short" }).toUpperCase()
  };
};

const formatTijuanaTime = (date) => {
  if (!date || Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Tijuana",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
};

const getStartDate = (game) => {
  if (game?.gameTimeUTC) {
    const date = new Date(game.gameTimeUTC);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  if (game?.gameEt) {
    const date = new Date(game.gameEt);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  return null;
};

const loadSchedule = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const data = await fetchCdnScoreboard();
    if (!data?.success) {
      error.value = data?.error || "No se pudo cargar el scoreboard.";
      games.value = [];
      return;
    }
    const scoreboard = data?.scoreboard?.scoreboard || {};
    const scoreboardGames = scoreboard?.games || [];
    dateLabel.value = formatScoreboardDate(scoreboard?.gameDate);
    const now = new Date();
    games.value = scoreboardGames.map((game) => {
      const away = game.awayTeam || {};
      const home = game.homeTeam || {};
      const statusText = (game.gameStatusText || "").trim();
      const startDate = getStartDate(game);
      const minutesToStart = startDate ? (startDate - now) / 60000 : null;
      const isScheduled = game.gameStatus === 1;
      const isPregame = isScheduled && minutesToStart !== null && minutesToStart <= 30 && minutesToStart >= 0;
      let time = "";
      let label = "";
      if (isScheduled) {
        time = formatTijuanaTime(startDate) || "Hora por confirmar";
        label = isPregame ? "PRE GAME" : "";
      } else {
        time = statusText || (game.gameStatus === 3 ? "Final" : "");
      }
      return {
        gameId: game.gameId,
        label,
        time,
        gameDate: scoreboard?.gameDate || "",
        gameStatus: game.gameStatus,
        gameStatusText: statusText,
        gameClock: game.gameClock || "",
        gamePeriod: game.period ?? null,
        gameTimeUTC: game.gameTimeUTC || "",
        awayName: away.teamName || away.teamTricode || "Away",
        homeName: home.teamName || home.teamTricode || "Home",
        awayTricode: away.teamTricode || "",
        homeTricode: home.teamTricode || "",
        awayScore: away.score ?? null,
        homeScore: home.score ?? null,
        awayRecord: formatRecord(away.wins, away.losses),
        homeRecord: formatRecord(home.wins, home.losses),
        awayLogo: getTeamLogo(away.teamId),
        homeLogo: getTeamLogo(home.teamId)
      };
    });
    emit("loaded", games.value);
  } catch (err) {
    error.value = err?.message || "Error inesperado al cargar el scoreboard.";
    games.value = [];
  } finally {
    isLoading.value = false;
  }
};

const handleSelect = (game) => {
  emit("select", game);
};

onMounted(loadSchedule);
</script>

<style scoped>
.schedule {
  width: 100%;
  padding: 8px 12px 0;
}

.schedule-status {
  min-height: 24px;
}

.muted {
  color: #6b7280;
  margin: 4px 0 0;
}

.error {
  color: #b91c1c;
  margin: 4px 0 0;
}

.schedule-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: center;
  width: 100%;
}

.schedule-date {
  width: 72px;
  min-height: 120px;
  border-radius: 12px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  display: grid;
  place-items: center;
  padding: 8px 6px;
  text-align: center;
  font-weight: 700;
  color: #0f172a;
}

.schedule-date__weekday {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #ef4444;
}

.schedule-date__day {
  font-size: 20px;
}

.schedule-date__month {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #64748b;
}

.schedule-strip {
  overflow: hidden;
  width: 100%;
}

.schedule-strip__list {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(240px, 1fr);
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  scrollbar-width: thin;
}

.schedule-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  padding: 16px;
  display: grid;
  gap: 12px;
  min-height: 120px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  cursor: pointer;
}

.schedule-card:hover {
  transform: translateY(-2px);
  border-color: #cbd5f5;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
}

.schedule-card--active {
  border-color: #6366f1;
  box-shadow: 0 10px 20px rgba(79, 70, 229, 0.18);
}

.schedule-card--loading {
  background: #e5e7eb;
  border-color: #cbd5f5;
  color: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.6);
}

.schedule-card--loading .time,
.schedule-card--loading .team span,
.schedule-card--loading .record {
  color: #ffffff;
}

.schedule-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.badge {
  font-size: 12px;
  font-weight: 700;
  color: #b91c1c;
}

.time {
  color: #0f172a;
  font-weight: 600;
  font-size: 13px;
}

.schedule-card__teams {
  display: grid;
  gap: 8px;
}

.team-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.team {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.team img {
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.record {
  color: #64748b;
  font-weight: 600;
  font-size: 12px;
}
</style>
