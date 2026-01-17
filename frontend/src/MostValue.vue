<template>
  <main class="most-value">
    <header class="most-value__header">
      <button class="ghost ghost--back" type="button" @click="goBack">Volver</button>
      <h1>Mayores Valores</h1>
    </header>

    <section class="most-value__section">
      <h2>80-100% (Rojo)</h2>
      <div v-if="topRed.length === 0" class="empty">Sin jugadores en este rango.</div>
      <div class="player-row" v-else>
        <article v-for="player in topRed" :key="player.key" class="player-card player-card--red">
          <div class="player-card__top">
            <span class="position-chip">{{ player.position }}</span>
            <span class="team-chip">{{ player.team }}</span>
          </div>
          <div class="player-card__avatar">
            <img v-if="player.photo" :src="player.photo" :alt="player.name" />
            <div v-else class="avatar-fallback"></div>
          </div>
          <p class="player-card__name">{{ player.name }}</p>
          <p class="player-card__prob">{{ player.label }}</p>
          <div class="player-card__stats">
            <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'points' }">
              <span class="stat-label">PTS</span>
              <span class="stat-value">{{ formatLine(player.pointsLine) }}</span>
            </div>
            <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'rebounds' }">
              <span class="stat-label">REB</span>
              <span class="stat-value">{{ formatLine(player.reboundsLine) }}</span>
            </div>
            <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'assists' }">
              <span class="stat-label">AST</span>
              <span class="stat-value">{{ formatLine(player.assistsLine) }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="most-value__section">
      <h2>70-79% (Azul)</h2>
      <div v-if="topBlue.length === 0" class="empty">Sin jugadores en este rango.</div>
      <div class="player-row" v-else>
        <article v-for="player in topBlue" :key="player.key" class="player-card player-card--platinum">
          <div class="player-card__top">
            <span class="position-chip">{{ player.position }}</span>
            <span class="team-chip">{{ player.team }}</span>
          </div>
          <div class="player-card__avatar">
            <img v-if="player.photo" :src="player.photo" :alt="player.name" />
            <div v-else class="avatar-fallback"></div>
          </div>
          <p class="player-card__name">{{ player.name }}</p>
          <p class="player-card__prob">{{ player.label }}</p>
          <div class="player-card__stats">
            <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'points' }">
              <span class="stat-label">PTS</span>
              <span class="stat-value">{{ formatLine(player.pointsLine) }}</span>
            </div>
            <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'rebounds' }">
              <span class="stat-label">REB</span>
              <span class="stat-value">{{ formatLine(player.reboundsLine) }}</span>
            </div>
            <div class="stat-row" :class="{ 'stat-row--best': player.bestStat === 'assists' }">
              <span class="stat-label">AST</span>
              <span class="stat-value">{{ formatLine(player.assistsLine) }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from "vue";

const LINEUPS_CACHE_KEY = "livenba_lineups_cache";

const readLineupsCache = () => {
  try {
    const stored = localStorage.getItem(LINEUPS_CACHE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
};

const lineupsCache = ref(readLineupsCache());

const formatLine = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return Number(value).toFixed(1);
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

const getBestStatType = (player) => {
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
  return candidates.sort((a, b) => b.percent - a.percent)[0].type;
};

const buildPlayer = (player, teamAbbr) => {
  const best = getBestStatType(player);
  if (!best) {
    return null;
  }
  const probability = getStatProbability(player.over_under_history, best);
  if (!probability) {
    return null;
  }
  const typeLabel = best === "points" ? "PTS" : best === "rebounds" ? "REB" : "AST";
  return {
    key: `${teamAbbr}-${player.player_id}`,
    name: player.player_name,
    photo: player.player_photo_url,
    position: player.position || "BENCH",
    team: teamAbbr,
    pointsLine: player.points_line,
    reboundsLine: player.rebounds_line,
    assistsLine: player.assists_line,
    bestStat: best,
    label: `${typeLabel} ${probability.side} ${probability.percent.toFixed(0)}%`,
    percent: probability.percent
  };
};

const allPlayers = computed(() => {
  const result = [];
  Object.values(lineupsCache.value).forEach((games) => {
    if (!Array.isArray(games)) {
      return;
    }
    games.forEach((game) => {
      if (!game?.lineups) {
        return;
      }
      const lineups = game.lineups || {};
      Object.keys(lineups).forEach((teamKey) => {
        const teamLineup = lineups[teamKey];
        ["PG", "SG", "SF", "PF", "C"].forEach((position) => {
          const player = teamLineup?.[position];
          if (!player || player.points_line == null) {
            return;
          }
          const built = buildPlayer({ ...player, position }, teamKey);
          if (built) {
            result.push(built);
          }
        });
        if (Array.isArray(teamLineup?.BENCH)) {
          teamLineup.BENCH.forEach((player) => {
            if (!player || player.points_line == null) {
              return;
            }
            const built = buildPlayer({ ...player, position: "BENCH" }, teamKey);
            if (built) {
              result.push(built);
            }
          });
        }
      });
    });
  });
  return result;
});

const topRed = computed(() => allPlayers.value.filter((p) => p.percent >= 80));
const topBlue = computed(() => allPlayers.value.filter((p) => p.percent >= 70 && p.percent < 80));

const goBack = () => {
  window.location.assign("/");
};
</script>

<style scoped>
.most-value {
  min-height: 100vh;
  padding: 24px;
  background: #f8fafc;
  color: #0f172a;
}

.most-value__header {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 20px;
}

.ghost {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.ghost--back {
  position: absolute;
  left: 0;
  top: 0;
}

.most-value__section {
  margin-bottom: 28px;
}

.player-row {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 220px;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 6px;
}

.empty {
  color: #64748b;
}

.player-card {
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 12px 14px 14px;
  display: grid;
  gap: 10px;
  background: #ffffff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  width: 220px;
  min-height: 360px;
}

.player-card--red {
  border-color: #ef4444;
  box-shadow: 0 10px 20px rgba(239, 68, 68, 0.2);
}

.player-card--platinum {
  border-color: #6366f1;
  box-shadow: 0 10px 20px rgba(99, 102, 241, 0.2);
}

.player-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.team-chip {
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
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

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.stat-row--best {
  background: #dcfce7;
  border: 1px solid #22c55e;
  color: #14532d;
}
</style>
