<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <header class="modal__header">
        <div class="modal__title">
          <h3>{{ player?.name || "Game Logs" }}</h3>
          <p class="muted" v-if="playerLine">
            Linea actual: {{ playerLine }}
          </p>
        </div>
        <button class="modal__close" type="button" @click="emit('close')">✕</button>
      </header>

      <div class="modal__body">
        <div v-if="isLoading" class="muted">Cargando game logs...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="!logs.length" class="muted">No hay game logs disponibles.</div>

        <div v-else class="logs-section">
          <div class="stat-tabs">
            <button
              v-for="stat in stats"
              :key="stat.key"
              type="button"
              class="stat-tab"
              :class="{ 'stat-tab--active': stat.key === selectedStat }"
              @click="selectedStat = stat.key"
            >
              {{ stat.label }}
            </button>
          </div>

          <div class="stat-summary">
            <span>Total: <strong>{{ statSummary.total }}</strong></span>
            <span>OVER: <strong class="text-over">{{ statSummary.over }}</strong></span>
            <span>UNDER: <strong class="text-under">{{ statSummary.under }}</strong></span>
            <span>Linea: <strong>{{ currentLine || "--" }}</strong></span>
          </div>

          <table class="logs-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>MIN</th>
              <th>{{ statLabel }}</th>
              <th>ROL</th>
              <th>Linea</th>
              <th>O/U</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="logKey(log)">
              <td>{{ formatDate(log.game_date) }}</td>
              <td>{{ formatNumber(log.minutes_played) }}</td>
              <td>{{ formatNumber(getStatValue(log)) }}</td>
              <td>{{ formatRole(log) }}</td>
              <td>{{ currentLine || "--" }}</td>
              <td>{{ getOutcome(getStatValue(log)) }}</td>
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  logs: { type: Array, default: () => [] },
  isLoading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  player: { type: Object, default: null }
});

const emit = defineEmits(["close"]);

const stats = [
  { key: "points", label: "Puntos", lineKey: "pointsLine" },
  { key: "assists", label: "Asistencias", lineKey: "assistsLine" },
  { key: "rebounds", label: "Rebotes", lineKey: "reboundsLine" }
];

const selectedStat = ref("points");

const formatDate = (value) => {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleDateString("en-US", { month: "short", day: "2-digit" });
};

const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return Number(value).toFixed(0);
};

const formatRole = (log) => {
  if (log.start_position) {
    return log.start_position;
  }
  if (log.starter_status) {
    return log.starter_status;
  }
  return "--";
};

const logKey = (log) => `${log.game_date}-${log.matchup}-${log.points}`;

const statLabel = computed(() => {
  const stat = stats.find((item) => item.key === selectedStat.value);
  return stat?.label || "Puntos";
});

const currentLine = computed(() => {
  const stat = stats.find((item) => item.key === selectedStat.value);
  const line = stat?.lineKey ? props.player?.[stat.lineKey] : null;
  if (line === null || line === undefined || Number.isNaN(line)) {
    return "";
  }
  return Number(line).toFixed(1);
});

const getStatValue = (log) => {
  if (!log) {
    return null;
  }
  return log[selectedStat.value];
};

const statSummary = computed(() => {
  if (!props.logs?.length) {
    return { total: 0, over: 0, under: 0 };
  }
  let total = 0;
  let over = 0;
  let under = 0;
  const line = Number(currentLine.value);
  props.logs.forEach((log) => {
    const value = Number(getStatValue(log));
    if (Number.isNaN(value)) {
      return;
    }
    total += 1;
    if (!Number.isNaN(line)) {
      if (value > line) {
        over += 1;
      } else {
        under += 1;
      }
    }
  });
  return { total, over, under };
});

const getOutcome = (value) => {
  const line = Number(currentLine.value);
  if (line === null || line === undefined || Number.isNaN(line)) {
    return "--";
  }
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return Number(value) > Number(line) ? "OVER" : "UNDER";
};
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  z-index: 50;
  padding: 16px;
}

.modal {
  width: min(980px, 100%);
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.2);
  overflow: hidden;
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.modal__title h3 {
  margin: 0 0 4px;
}

.modal__close {
  border: none;
  background: #f1f5f9;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
}

.modal__body {
  padding: 16px 20px 24px;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.logs-table th,
.logs-table td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid #e5e7eb;
}

.logs-table th {
  color: #64748b;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 11px;
}

.logs-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-tab {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  padding: 6px 12px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.stat-tab--active {
  border-color: #4f46e5;
  background: #eef2ff;
  color: #4338ca;
}

.stat-summary {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  color: #475569;
  font-size: 13px;
}

.text-over {
  color: #1d4ed8;
}

.text-under {
  color: #b91c1c;
}

.muted {
  color: #6b7280;
}

.error {
  color: #b91c1c;
}
</style>
