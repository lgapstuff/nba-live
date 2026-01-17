<template>
  <main class="styles-page">
    <header class="styles-header">
      <h1>Live Stats Styles</h1>
      <p>Simulacion de estilos para PTS/AST/REB/PF/MIN + estado.</p>
      <div class="styles-actions">
        <span class="tag">Ruta: /styles</span>
        <span class="tag">Datos simulados</span>
      </div>
    </header>

    <section class="styles-grid">
      <article class="style-card">
        <h2>Style 1 - Barra compacta</h2>
        <div class="style-one">
          <span class="chip">PTS <strong>{{ sample.pts }}</strong></span>
          <span class="chip">AST <strong>{{ sample.ast }}</strong></span>
          <span class="chip">REB <strong>{{ sample.reb }}</strong></span>
          <span class="chip">PF <strong>{{ sample.pf }}</strong></span>
          <span class="chip">MIN <strong>{{ sample.min }}</strong></span>
          <span class="status-pill status-pill--live">{{ sample.status }}</span>
        </div>
      </article>

      <article class="style-card">
        <h2>Style 2 - Dos filas minimal</h2>
        <div class="style-two">
          <div class="row">
            <div class="mini">
              <span class="label">PTS</span>
              <span class="value">{{ sample.pts }}</span>
            </div>
            <div class="mini">
              <span class="label">AST</span>
              <span class="value">{{ sample.ast }}</span>
            </div>
            <div class="mini">
              <span class="label">REB</span>
              <span class="value">{{ sample.reb }}</span>
            </div>
          </div>
          <div class="row">
            <div class="mini">
              <span class="label">PF</span>
              <span class="value">{{ sample.pf }}</span>
            </div>
            <div class="mini">
              <span class="label">MIN</span>
              <span class="value">{{ sample.min }}</span>
            </div>
            <div class="mini">
              <span class="label">ESTADO</span>
              <span class="value value--status">{{ sample.status }}</span>
            </div>
          </div>
        </div>
      </article>

      <article class="style-card">
        <h2>Style 3 - Micro cards + header</h2>
        <div class="style-three">
          <div class="status-header">{{ sample.status }}</div>
          <div class="micro-grid">
            <div class="micro-card">
              <span class="abbr">PTS</span>
              <span class="micro-value">{{ sample.pts }}</span>
            </div>
            <div class="micro-card">
              <span class="abbr">AST</span>
              <span class="micro-value">{{ sample.ast }}</span>
            </div>
            <div class="micro-card">
              <span class="abbr">REB</span>
              <span class="micro-value">{{ sample.reb }}</span>
            </div>
            <div class="micro-card">
              <span class="abbr">PF</span>
              <span class="micro-value">{{ sample.pf }}</span>
            </div>
            <div class="micro-card">
              <span class="abbr">MIN</span>
              <span class="micro-value">{{ sample.min }}</span>
            </div>
          </div>
        </div>
      </article>

      <article class="style-card">
        <h2>Style 4 - Lista vertical</h2>
        <div class="style-four">
          <div class="line"><span>PTS</span><strong>{{ sample.pts }}</strong></div>
          <div class="line"><span>AST</span><strong>{{ sample.ast }}</strong></div>
          <div class="line"><span>REB</span><strong>{{ sample.reb }}</strong></div>
          <div class="line"><span>PF</span><strong>{{ sample.pf }}</strong></div>
          <div class="line"><span>MIN</span><strong>{{ sample.min }}</strong></div>
          <div class="line line--status">{{ sample.status }}</div>
        </div>
      </article>

      <article class="style-card">
        <h2>Style 5 - Segmented pill</h2>
        <div class="style-five">
          <div class="segments">
            <span>PTS <strong>{{ sample.pts }}</strong></span>
            <span>AST <strong>{{ sample.ast }}</strong></span>
            <span>REB <strong>{{ sample.reb }}</strong></span>
            <span>PF <strong>{{ sample.pf }}</strong></span>
            <span>MIN <strong>{{ sample.min }}</strong></span>
          </div>
          <div class="status-tag">{{ sample.status }}</div>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup>
const sample = {
  pts: 18,
  ast: 4,
  reb: 7,
  pf: 2,
  min: "21:34",
  status: "EN CANCHA"
};
</script>

<style scoped>
.styles-page {
  min-height: 100vh;
  padding: 24px 24px 48px;
  background: #f8fafc;
  color: #0f172a;
}

.styles-header {
  margin-bottom: 20px;
}

.styles-header h1 {
  margin: 0 0 6px;
  font-size: 24px;
}

.styles-header p {
  margin: 0 0 12px;
  color: #64748b;
}

.styles-actions {
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

.styles-grid {
  display: grid;
  gap: 16px;
}

.style-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 18px rgba(15, 23, 42, 0.08);
}

.style-card h2 {
  margin: 0 0 10px;
  font-size: 16px;
}

.style-one {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}

.chip strong {
  color: #0f172a;
}

.status-pill {
  background: #111827;
  color: #ffffff;
  padding: 6px 12px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
}

.status-pill--live {
  background: #16a34a;
}

.style-two {
  display: grid;
  gap: 10px;
}

.style-two .row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 10px;
}

.mini {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px;
  display: grid;
  gap: 4px;
}

.mini .label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 700;
}

.mini .value {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
}

.value--status {
  font-size: 11px;
  color: #16a34a;
}

.style-three {
  display: grid;
  gap: 10px;
}

.status-header {
  background: #0f172a;
  color: #ffffff;
  padding: 6px 12px;
  border-radius: 999px;
  width: fit-content;
  font-weight: 800;
  font-size: 12px;
}

.micro-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(86px, 1fr));
  gap: 8px;
}

.micro-card {
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 8px;
  display: grid;
  gap: 4px;
}

.abbr {
  font-size: 11px;
  color: #64748b;
  font-weight: 700;
}

.micro-value {
  font-size: 16px;
  font-weight: 800;
}

.style-four {
  display: grid;
  gap: 8px;
}

.style-four .line {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f1f5f9;
  font-weight: 700;
}

.style-four .line--status {
  justify-content: center;
  background: #1d4ed8;
  color: #ffffff;
  font-weight: 800;
}

.style-five {
  display: grid;
  gap: 10px;
}

.segments {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(92px, 1fr));
  gap: 6px;
  background: #0f172a;
  padding: 6px;
  border-radius: 14px;
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 700;
}

.segments span {
  background: rgba(255, 255, 255, 0.08);
  padding: 8px;
  border-radius: 10px;
  text-align: center;
}

.segments strong {
  display: block;
  color: #ffffff;
  font-size: 14px;
}

.status-tag {
  background: #16a34a;
  color: #ffffff;
  padding: 8px 12px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
  width: fit-content;
}
</style>
