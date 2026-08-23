const runsList = document.getElementById("runs-list");
const detail = document.getElementById("detail");
const memoryList = document.getElementById("memory-list");
const notifList = document.getElementById("notif-list");
const runStatus = document.getElementById("run-status");

function pillClass(status) {
  if (status === "approved") return "pill pill-approved";
  if (status === "rejected") return "pill pill-rejected";
  return "pill pill-pending";
}
function pillLabel(status) {
  return { pending_approval: "待审批", approved: "已批准", rejected: "已拒绝" }[status] || status;
}
function pct(x) { return (x * 100).toFixed(1) + "%"; }

function citationsBlock(citations) {
  if (!citations || !citations.length) {
    return `<p class="hint">未检索到足够相关的历史案例（RAG 降级：不注入不相关内容）</p>`;
  }
  return `<div class="citation-list">${citations.map(c => `
    <div class="citation-item">
      <a href="${c.source_url}" target="_blank" rel="noopener">[${c.n}] ${c.scene}</a>
      <span class="citation-score">score ${c.score}</span>
      ${c.confidence === "secondary" ? `<span class="badge">二手引用</span>` : ""}
      <p class="citation-lesson">${c.lesson}（效果：${c.lift}）</p>
    </div>
  `).join("")}</div>`;
}

async function loadRuns() {
  const runs = await (await fetch("/api/runs")).json();
  runsList.innerHTML = runs.map(r => `
    <div class="run-item" onclick="showRun('${r.id}')">
      <span class="g">${r.goal}<span class="${pillClass(r.status)}">${pillLabel(r.status)}</span></span>
      <span class="meta">${new Date(r.created_at).toLocaleString()}</span>
    </div>
  `).join("") || `<p class="hint">还没有运行记录</p>`;
}

async function loadMemory() {
  const items = await (await fetch("/api/memory")).json();
  memoryList.innerHTML = items.map(m => `
    <div class="run-item">
      <span class="g">${m.hypothesis}</span>
      <span class="meta">${m.result} · 置信度 ${(m.confidence * 100).toFixed(0)}%</span>
    </div>
  `).join("") || `<p class="hint">暂无记忆记录，批准或拒绝一次实验后会出现在这里</p>`;
}

async function loadNotifications() {
  const items = await (await fetch("/api/notifications")).json();
  notifList.innerHTML = items.map(n => `
    <div class="n-item">[${n.channel}] ${n.content}</div>
  `).join("") || `<p class="hint">暂无通知</p>`;
}

async function showRun(id) {
  const r = await (await fetch(`/api/runs/${id}`)).json();
  const o = r.opportunity, e = r.experiment, s = r.simulation, c = r.critic;
  detail.className = "card detail";
  detail.innerHTML = `
    <h2>${r.goal} <span class="${pillClass(r.status)}">${pillLabel(r.status)}</span></h2>

    <div class="section-block">
      <h3>Opportunity</h3>
      <p>${o.description}</p>
      <table class="kv">
        <tr><td>环节</td><td>${o.from_step} → ${o.to_step}</td></tr>
        <tr><td>用户数</td><td>${o.from_users} → ${o.to_users}</td></tr>
        <tr><td>流失率</td><td>${pct(o.drop_rate)}</td></tr>
      </table>
      <h3 class="citation-h3">RAG 检索到的参考案例</h3>
      ${citationsBlock(o.citations)}
    </div>

    <div class="section-block">
      <h3>Experiment</h3>
      <p>${e.narrative}</p>
      <table class="kv">
        <tr><td>A 组</td><td>${e.variant_a.desc}</td></tr>
        <tr><td>B 组</td><td>${e.variant_b.desc}</td></tr>
        <tr><td>提议预算 / 上限</td><td>¥${e.proposed_budget.toFixed(0)} / ¥${e.budget_limit.toFixed(0)}</td></tr>
      </table>
      <h3 class="citation-h3">RAG 检索到的参考案例</h3>
      ${citationsBlock(e.citations)}
    </div>

    <div class="section-block">
      <h3>Critic 校验</h3>
      ${c.passed
        ? `<p style="color:var(--good)">通过：预算与数字均可追溯到原始数据</p>`
        : `<div class="issues">${c.issues.map(i => `<p>⚠ ${i}</p>`).join("")}</div>`}
    </div>

    <div class="section-block">
      <h3>Simulation（仅用于排序，不代表真实结果）</h3>
      <p>${s.summary}</p>
      <table class="kv">
        <tr><td>预期提升区间</td><td>${pct(s.lift_low)} ~ ${pct(s.lift_high)}</td></tr>
        <tr><td>置信度</td><td>${(s.confidence * 100).toFixed(0)}%</td></tr>
        <tr><td>方向</td><td>${s.direction === "positive" ? "正向" : "负向"}</td></tr>
      </table>
    </div>

    ${r.status === "pending_approval" ? `
      <div class="actions">
        <button class="btn-approve" onclick="decide('${r.id}','approved')">批准并写回</button>
        <button class="btn-reject" onclick="decide('${r.id}','rejected')">拒绝</button>
      </div>
    ` : ""}
  `;
}

async function decide(id, decision) {
  await fetch(`/api/runs/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
  await Promise.all([loadRuns(), loadMemory(), loadNotifications()]);
  showRun(id);
}

document.getElementById("run-btn").addEventListener("click", async () => {
  const goal = document.getElementById("goal-input").value.trim();
  const budget = parseFloat(document.getElementById("budget-input").value);
  if (!goal) return;
  runStatus.textContent = "Agent 正在分析…";
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal, budget_limit: budget }),
  });
  const r = await res.json();
  runStatus.textContent = "完成";
  await loadRuns();
  showRun(r.id);
});

async function loadCorpus() {
  const corpusList = document.getElementById("corpus-list");
  const items = await (await fetch("/api/corpus")).json();
  corpusList.innerHTML = items.map(c => `
    <div class="corpus-card">
      <a class="title" href="${c.source_url}" target="_blank" rel="noopener">
        ${c.scene}
        <span class="badge">${c.confidence === "secondary" ? "二手引用" : "一手来源"}</span>
      </a>
      <div class="scene">${c.channel} · ${c.source}</div>
      <div class="lift">${c.lift}</div>
      <div class="lesson">${c.lesson}</div>
    </div>
  `).join("") || `<p class="hint">暂无语料，检查 packages/corpus/curated/*.jsonl</p>`;
}

loadRuns();
loadMemory();
loadNotifications();
loadCorpus();
