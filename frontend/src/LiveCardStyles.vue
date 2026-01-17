<template>
  <main class="cards-page">
    <header class="cards-header">
      <h1>Player Card Styles</h1>
      <p>5 variantes de tarjeta con datos simulados.</p>
      <div class="tags">
        <span class="tag">Ruta: /cards</span>
        <span class="tag">Jugador demo</span>
      </div>
    </header>

    <section class="cards-grid">
      <article class="card card--style-one">
        <div class="card-top">
          <span class="pill">{{ player.position }}</span>
          <span class="role">{{ player.role }}</span>
        </div>
        <div class="avatar">
          <div class="avatar-circle"></div>
        </div>
        <h3>{{ player.name }}</h3>
        <p class="sub">{{ player.team }}</p>
        <div class="lines">
          <div class="line"><span>PTS</span><strong>{{ player.pointsLine }}</strong></div>
          <div class="line"><span>REB</span><strong>{{ player.reboundsLine }}</strong></div>
          <div class="line"><span>AST</span><strong>{{ player.assistsLine }}</strong></div>
        </div>
        <div class="live-row">
          <span>{{ player.live.pts }} PTS</span>
          <span>{{ player.live.ast }} AST</span>
          <span>{{ player.live.reb }} REB</span>
          <span>{{ player.live.min }} MIN</span>
        </div>
        <div class="status">{{ player.status }}</div>
      </article>

      <article class="card card--style-two">
        <div class="header-row">
          <div>
            <h3>{{ player.name }}</h3>
            <span class="muted">{{ player.team }} · {{ player.position }}</span>
          </div>
          <span class="badge">{{ player.status }}</span>
        </div>
        <div class="stat-grid">
          <div class="stat-box">
            <span>PTS</span>
            <strong>{{ player.live.pts }}</strong>
          </div>
          <div class="stat-box">
            <span>AST</span>
            <strong>{{ player.live.ast }}</strong>
          </div>
          <div class="stat-box">
            <span>REB</span>
            <strong>{{ player.live.reb }}</strong>
          </div>
          <div class="stat-box">
            <span>PF</span>
            <strong>{{ player.live.pf }}</strong>
          </div>
          <div class="stat-box">
            <span>MIN</span>
            <strong>{{ player.live.min }}</strong>
          </div>
        </div>
        <div class="odds-row">
          <span>PTS {{ player.pointsLine }}</span>
          <span>REB {{ player.reboundsLine }}</span>
          <span>AST {{ player.assistsLine }}</span>
        </div>
      </article>

      <article class="card card--style-three">
        <div class="side-accent"></div>
        <div class="content">
          <div class="mini-header">
            <span class="pill">{{ player.position }}</span>
            <span class="status-pill">{{ player.status }}</span>
          </div>
          <h3>{{ player.name }}</h3>
          <div class="stat-row">
            <div class="stat-chip"><strong>{{ player.live.pts }}</strong> PTS</div>
            <div class="stat-chip"><strong>{{ player.live.ast }}</strong> AST</div>
            <div class="stat-chip"><strong>{{ player.live.reb }}</strong> REB</div>
          </div>
          <div class="meta-row">
            <span>PF {{ player.live.pf }}</span>
            <span>MIN {{ player.live.min }}</span>
            <span>{{ player.role }}</span>
          </div>
          <div class="lines-row">
            <span>PTS {{ player.pointsLine }}</span>
            <span>REB {{ player.reboundsLine }}</span>
            <span>AST {{ player.assistsLine }}</span>
          </div>
        </div>
      </article>

      <article class="card card--style-four">
        <div class="avatar-block">
          <div class="avatar-circle"></div>
          <div>
            <h3>{{ player.name }}</h3>
            <span class="muted">{{ player.team }}</span>
          </div>
        </div>
        <div class="pill-row">
          <span class="pill">{{ player.position }}</span>
          <span class="pill">{{ player.role }}</span>
          <span class="pill pill--dark">{{ player.status }}</span>
        </div>
        <div class="split">
          <div>
            <div class="mini-line">PTS <strong>{{ player.pointsLine }}</strong></div>
            <div class="mini-line">REB <strong>{{ player.reboundsLine }}</strong></div>
            <div class="mini-line">AST <strong>{{ player.assistsLine }}</strong></div>
          </div>
          <div class="live-stack">
            <span>{{ player.live.pts }} PTS</span>
            <span>{{ player.live.ast }} AST</span>
            <span>{{ player.live.reb }} REB</span>
            <span>{{ player.live.pf }} PF</span>
            <span>{{ player.live.min }} MIN</span>
          </div>
        </div>
      </article>

      <article class="card card--style-five">
        <div class="top-row">
          <span class="pill pill--blue">{{ player.position }}</span>
          <span class="status-pill">{{ player.status }}</span>
        </div>
        <h3>{{ player.name }}</h3>
        <div class="live-grid">
          <div class="live-cell">
            <span>PTS</span>
            <strong>{{ player.live.pts }}</strong>
          </div>
          <div class="live-cell">
            <span>AST</span>
            <strong>{{ player.live.ast }}</strong>
          </div>
          <div class="live-cell">
            <span>REB</span>
            <strong>{{ player.live.reb }}</strong>
          </div>
          <div class="live-cell">
            <span>PF</span>
            <strong>{{ player.live.pf }}</strong>
          </div>
          <div class="live-cell">
            <span>MIN</span>
            <strong>{{ player.live.min }}</strong>
          </div>
        </div>
        <div class="bottom-row">
          <span>PTS {{ player.pointsLine }}</span>
          <span>REB {{ player.reboundsLine }}</span>
          <span>AST {{ player.assistsLine }}</span>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup>
const player = {
  name: "Jaren Jackson Jr.",
  team: "Memphis Grizzlies",
  position: "PF",
  role: "STARTER",
  pointsLine: "27.5",
  reboundsLine: "7.5",
  assistsLine: "3.5",
  status: "EN CANCHA",
  live: {
    pts: 18,
    ast: 3,
    reb: 6,
    pf: 2,
    min: "21:34"
  }
};
</script>

<style scoped>
.cards-page {
  min-height: 100vh;
  padding: 24px 24px 48px;
  background: #f8fafc;
  color: #0f172a;
}

.cards-header h1 {
  margin: 0 0 6px;
  font-size: 24px;
}

.cards-header p {
  margin: 0 0 12px;
  color: #64748b;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  background: #e2e8f0;
  color: #475569;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.cards-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.card {
  background: #ffffff;
  border-radius: 16px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 18px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 10px;
  position: relative;
  overflow: hidden;
}

.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: #e0e7ff;
  color: #1d4ed8;
}

.pill--dark {
  background: #111827;
  color: #ffffff;
}

.pill--blue {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: #16a34a;
  color: #ffffff;
  font-size: 11px;
  font-weight: 800;
}

.avatar {
  display: grid;
  place-items: center;
}

.avatar-circle {
  width: 60px;
  height: 60px;
  border-radius: 999px;
  background: radial-gradient(circle at 30% 30%, #c7d2fe, #6366f1);
  box-shadow: 0 8px 16px rgba(79, 70, 229, 0.3);
}

.card h3 {
  margin: 0;
}

.sub {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

.lines {
  display: grid;
  gap: 6px;
}

.line {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f8fafc;
  border-radius: 10px;
  font-weight: 700;
  color: #475569;
}

.live-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #0f172a;
  font-weight: 700;
}

.status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  color: #ffffff;
  border-radius: 999px;
  padding: 6px 12px;
  font-weight: 800;
  font-size: 11px;
}

.card--style-two .header-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.card--style-two .muted {
  color: #94a3b8;
  font-size: 12px;
}

.card--style-two .badge {
  background: #0f172a;
  color: #ffffff;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 8px;
}

.stat-box {
  background: #f1f5f9;
  border-radius: 12px;
  padding: 8px;
  display: grid;
  gap: 4px;
  text-align: center;
  font-size: 11px;
  color: #64748b;
  font-weight: 700;
}

.stat-box strong {
  color: #0f172a;
  font-size: 14px;
}

.odds-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.card--style-three {
  padding-left: 20px;
}

.side-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6px;
  background: linear-gradient(180deg, #6366f1, #22c55e);
}

.card--style-three .content {
  display: grid;
  gap: 10px;
}

.mini-header {
  display: flex;
  gap: 6px;
  align-items: center;
}

.stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stat-chip {
  background: #0f172a;
  color: #ffffff;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 700;
}

.meta-row,
.lines-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

.card--style-four .avatar-block {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pill-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mini-line {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f8fafc;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
}

.live-stack {
  display: grid;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
}

.card--style-five .top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.live-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 8px;
}

.live-cell {
  background: #f8fafc;
  border-radius: 10px;
  padding: 8px;
  text-align: center;
  font-size: 11px;
  color: #64748b;
  font-weight: 700;
}

.live-cell strong {
  display: block;
  color: #0f172a;
  font-size: 14px;
}

.bottom-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #475569;
  font-weight: 700;
}
</style>
