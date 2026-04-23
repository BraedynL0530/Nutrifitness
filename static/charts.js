// ---- Toast notification (non-blocking) ----
function showToast(msg, duration) {
  duration = duration || 3000;
  var toast = document.getElementById('nf-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'nf-toast';
    toast.style.cssText = [
      'position:fixed', 'bottom:76px', 'left:50%', 'transform:translateX(-50%)',
      'background:rgba(26,8,37,0.97)', 'border:1px solid #8e44ad',
      'border-radius:10px', 'padding:10px 18px', 'color:#d8b4ff',
      'font-size:13px', 'z-index:2000', 'pointer-events:none',
      'opacity:0', 'transition:opacity 0.3s', 'text-align:center',
      'max-width:80vw'
    ].join(';');
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(function() { toast.style.opacity = '0'; }, duration);
}
function _guestKey() {
  const today = new Date().toISOString().split('T')[0];
  return 'guestFoodLog_' + today;
}

function getGuestFoodLog() {
  try { return JSON.parse(localStorage.getItem(_guestKey()) || '[]'); }
  catch(e) { return []; }
}

function saveGuestFoodLog(items) {
  try { localStorage.setItem(_guestKey(), JSON.stringify(items)); }
  catch(e) {}
}

// ---- Food mode tabs ----
function setFoodMode(mode) {
  ["scan", "search", "manual", "exercise"].forEach(m => {
    const el = document.getElementById(`${m}Mode`);
    if (el) el.style.display = m === mode ? "block" : "none";
    const btn = document.getElementById(`btn-${m}`);
    if (btn) btn.classList.toggle("active", m === mode);
  });
}

async function runFoodSearch() {
  const query = document.getElementById("foodSearchInput").value.trim();
  if (!query) return;
  const container = document.getElementById("searchResults");
  container.innerHTML = '<p style="color:#9b7acf;">Searching...</p>';
  try {
    const res = await fetch(`/api/food-search/?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (!data.results || data.results.length === 0) {
      container.innerHTML = '<p style="color:#9b7acf;">No results. Try manual entry.</p>';
      return;
    }
    container.innerHTML = data.results.map((food, i) => {
      const portionSize = food.portion_size || 100;
      const portionCals = ((food.nutrients?.calories_kcal || 0) * portionSize / 100).toFixed(0);
      return `
      <div style="background:rgba(155,89,182,0.15); border-radius:8px;
                  padding:10px; margin:6px 0; text-align:left;">
        <strong style="color:#d8b4ff;">${food.name || "Unknown"}</strong><br>
        <span style="color:#9b7acf; font-size:13px;">
          ${food.nutrients?.calories_kcal || "?"} kcal/100g | 
          P: ${food.nutrients?.proteins_g || "?"}g | 
          C: ${food.nutrients?.carbohydrates_g || "?"}g | 
          F: ${food.nutrients?.fat_g || "?"}g
        </span><br>
        <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
          <input type="number" id="sg${i}" value="${portionSize}" min="1"
                 style="width:65px; padding:5px; border:1px solid #8e44ad;
                        border-radius:6px; background:rgba(155,89,182,0.1); color:#d8b4ff;">
          <span style="color:#9b7acf; font-size:13px;">g</span>
          <button onclick='logSearchFood(${JSON.stringify(food).replace(/'/g, "&#39;")}, ${i})'
                  style="flex:1; padding:6px; background:#8e44ad; border:none;
                         border-radius:6px; color:white; cursor:pointer; font-weight:600;">
            Log
          </button>
          <button onclick='quickLogFood(${JSON.stringify(food).replace(/'/g, "&#39;")})'
                  title="Quick Log (1 serving = ${portionSize}g, ~${portionCals} kcal)"
                  style="padding:6px 10px; background:rgba(155,89,182,0.3); border:1px solid #8e44ad;
                         border-radius:6px; color:#d8b4ff; cursor:pointer; font-size:12px;">
            ⚡ 1 serving
          </button>
        </div>
      </div>
    `}).join("");
  } catch (e) {
    container.innerHTML = '<p style="color:#ff6b6b;">Search failed. Try again.</p>';
  }
}

async function quickLogFood(food) {
  const portionSize = food.portion_size || 100;
  await logFoodToServer(food, portionSize);
}

async function logSearchFood(food, index) {
  const grams = parseFloat(document.getElementById(`sg${index}`).value);
  if (!grams || grams <= 0) { alert("Enter valid grams."); return; }
  await logFoodToServer(food, grams);
}

async function logManualFood() {
  const name = document.getElementById("manualName").value.trim();
  const grams = parseFloat(document.getElementById("manualGrams").value);
  if (!name) { alert("Food name is required."); return; }
  if (!grams || grams <= 0) { alert("Enter valid grams."); return; }
  const food = {
    barcode: `manual_${Date.now()}`,
    name: name,
    nutrients: {
      calories_kcal: parseFloat(document.getElementById("manualCalories").value) || 0,
      proteins_g: parseFloat(document.getElementById("manualProtein").value) || 0,
      carbohydrates_g: parseFloat(document.getElementById("manualCarbs").value) || 0,
      fat_g: parseFloat(document.getElementById("manualFat").value) || 0,
    },
    micronutrients: {}
  };
  await logFoodToServer(food, grams);
}

async function logFoodToServer(food, grams) {
  if (typeof IS_GUEST !== 'undefined' && IS_GUEST) {
    // Guest mode: store in localStorage
    const multiplier = grams / 100;
    const logs = getGuestFoodLog();
    logs.push({
      name: food.name || "Unknown",
      grams: grams,
      calories: ((food.nutrients?.calories_kcal || 0) * multiplier).toFixed(0),
      protein:  ((food.nutrients?.proteins_g    || 0) * multiplier).toFixed(1),
      carbs:    ((food.nutrients?.carbohydrates_g || 0) * multiplier).toFixed(1),
      fat:      ((food.nutrients?.fat_g          || 0) * multiplier).toFixed(1),
    });
    saveGuestFoodLog(logs);
    showToast(food.name + ' logged! Login to save your data permanently.');
    location.reload();
    return;
  }

  const payload = {
    barcode: food.barcode || `manual_${Date.now()}`,
    name: food.name,
    grams: grams,
    nutrients: food.nutrients || {},
    micronutrients: food.micronutrients || {},
    category: food.category || "",
    allergens: food.allergens || []
  };
  try {
    const res = await fetch("/api/food-log/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      alert(`${food.name} logged!`);
      location.reload();
    } else {
      const err = await res.json();
      alert(err.error || "Failed to log food.");
    }
  } catch (e) {
    alert("Network error. Try again.");
  }
}

// ---- Load guest food log into the food list UI ----
function applyGuestFoodLog() {
  const logs = getGuestFoodLog();
  if (!logs.length) return;

  const foodLogEl = document.getElementById("foodLog");
  if (foodLogEl) {
    foodLogEl.innerHTML = logs
      .map(item => `<li>${item.name} — ${item.calories} kcal</li>`)
      .join("");
  }

  // Update calorie bar with guest totals
  const totalCals = logs.reduce((sum, f) => sum + parseFloat(f.calories || 0), 0);
  const chartData = JSON.parse(document.getElementById("chart-data").textContent);
  const goal = chartData.goal_calories || 2000;
  const percent = Math.min((totalCals / goal) * 100, 100);
  setTimeout(() => {
    const fill = document.getElementById("bar-fill");
    if (fill) fill.style.width = percent + "%";
  }, 100);
  const calText = document.getElementById("calorieText");
  if (calText) calText.innerText = `${Math.round(totalCals)} / ${goal} kcal consumed`;
  const remEl = document.getElementById("remainingText");
  if (remEl) {
    const rem = Math.round(goal - totalCals);
    remEl.innerText = rem >= 0 ? `✅ ${rem} kcal remaining` : `⚠️ ${Math.abs(rem)} kcal over goal`;
    remEl.style.color = rem >= 0 ? "#4caf7d" : "#ff6b6b";
    remEl.style.fontWeight = "600";
    remEl.style.fontSize = "13px";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`${targetTab}-tab`).classList.add("active");
    });
  });

  // ---------- Load data ----------
  const chartData = JSON.parse(document.getElementById("chart-data").textContent);
  const weightData = JSON.parse(document.getElementById("weight-data").textContent);
  const heatmapEl = document.getElementById("heatmap-data");
  const heatmapData = heatmapEl ? JSON.parse(heatmapEl.textContent) : [];
  const streakEl = document.getElementById("streak-info");
  const streakInfo = streakEl ? JSON.parse(streakEl.textContent) : {streak: 0, can_restore: false};

  // ---------- Streak display ----------
  const streakNumber = document.getElementById("streakNumber");
  if (streakNumber) streakNumber.textContent = streakInfo.streak || 0;

  // Streak badge → toggle heatmap popup
  const streakBadge = document.getElementById("streakCard");
  const heatmapPopup = document.getElementById("heatmapContainer");
  if (streakBadge && heatmapPopup) {
    streakBadge.addEventListener("click", (e) => {
      e.stopPropagation();
      heatmapPopup.classList.toggle("open");
    });
    // Close heatmap popup when clicking outside
    document.addEventListener("click", (e) => {
      if (!heatmapPopup.contains(e.target) && !streakBadge.contains(e.target)) {
        heatmapPopup.classList.remove("open");
      }
    });
  }

  const restoreBtn = document.getElementById("restoreBtn");
  if (restoreBtn) {
    if (typeof IS_PREMIUM !== 'undefined' && IS_PREMIUM && streakInfo.can_restore) {
      restoreBtn.style.display = "block";
      restoreBtn.addEventListener("click", async () => {
        restoreBtn.disabled = true;
        restoreBtn.textContent = "Restoring...";
        try {
          const res = await fetch("/api/streak-restore/", { method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
          });
          const data = await res.json();
          if (res.ok) {
            showToast("🔥 Streak restored! " + data.streak + " day streak!");
            if (streakNumber) streakNumber.textContent = data.streak;
            restoreBtn.style.display = "none";
          } else {
            showToast(data.error || "Could not restore streak.");
            restoreBtn.disabled = false;
            restoreBtn.textContent = "🔄 Restore";
          }
        } catch (e) {
          showToast("Network error. Try again.");
          restoreBtn.disabled = false;
          restoreBtn.textContent = "🔄 Restore";
        }
      });
    } else if (typeof IS_PREMIUM !== 'undefined' && IS_PREMIUM && streakInfo.restore_next_available) {
      restoreBtn.style.display = "block";
      restoreBtn.disabled = true;
      restoreBtn.textContent = `🔄 Restore (available ${streakInfo.restore_next_available})`;
    }
  }

  // ---------- 7-Day Activity Heatmap ----------
  const heatmapGrid = document.getElementById("heatmapGrid");
  if (heatmapGrid && heatmapData.length) {
    const maxCount = Math.max(...heatmapData.map(d => d.count), 1);
    heatmapData.forEach(day => {
      const cell = document.createElement("div");
      cell.className = "heatmap-cell";
      const intensity = day.count === 0 ? 0 : Math.max(0.2, day.count / maxCount);
      cell.style.background = day.count === 0
        ? "rgba(155,89,182,0.1)"
        : `rgba(176,132,247,${intensity})`;
      // Short date label (Mon, Tue...) — parse as local time
      const dateObj = new Date(day.date + "T00:00:00");  // local midnight
      const dayName = dateObj.toLocaleDateString('en', { weekday: 'short' });
      cell.title = `${day.date}: ${day.count} food${day.count !== 1 ? 's' : ''} logged`;
      const label = document.createElement("span");
      label.className = "heatmap-label";
      label.textContent = dayName;
      cell.appendChild(label);
      if (day.count > 0) {
        const num = document.createElement("span");
        num.className = "heatmap-count";
        num.textContent = day.count;
        cell.appendChild(num);
      }
      heatmapGrid.appendChild(cell);
    });
  }

  // ---------- Semicircle (macros) ----------
  const canvas = document.getElementById("macroChart");
  const ctx = canvas.getContext("2d");
  const macros = chartData.macros;
  const total = Object.values(macros).reduce((a, b) => a + b, 0);

  if (total === 0) {
    ctx.beginPath();
    ctx.arc(160, 140, 90, Math.PI, Math.PI * 2);
    ctx.lineWidth = 30;
    ctx.strokeStyle = "rgba(155,89,182,0.3)";
    ctx.stroke();
  } else {
    let start = Math.PI;
    const colors = ["#b084f7", "#8e44ad", "#6c3d99"];
    Object.entries(macros).forEach(([name, value], i) => {
      const angle = (value / total) * Math.PI;
      ctx.beginPath();
      ctx.arc(160, 140, 90, start, start + angle);
      ctx.lineWidth = 30;
      ctx.strokeStyle = colors[i];
      ctx.stroke();
      start += angle;
    });
  }

  // ---------- Calorie bar ----------
  const goal = chartData.goal_calories;
  const eaten = chartData.eaten_calories || 0;
  const remaining = Math.round((goal || 0) - eaten);
  const percent = Math.min((eaten / (goal || 1)) * 100, 100);
  setTimeout(() => {
    document.getElementById("bar-fill").style.width = percent + "%";
  }, 100);
  document.getElementById("calorieText").innerText = `${Math.round(eaten)} / ${goal} kcal consumed`;
  const remainingEl = document.getElementById("remainingText");
  if (remainingEl) {
    remainingEl.innerText = remaining >= 0
      ? `✅ ${remaining} kcal remaining`
      : `⚠️ ${Math.abs(remaining)} kcal over goal`;
    remainingEl.style.color = remaining >= 0 ? "#4caf7d" : "#ff6b6b";
    remainingEl.style.fontWeight = "600";
    remainingEl.style.fontSize = "13px";
    remainingEl.style.marginTop = "4px";
  }

  // ---------- Guest food log (override bar + list) ----------
  if (typeof IS_GUEST !== 'undefined' && IS_GUEST) {
    applyGuestFoodLog();
  }

  // ---------- Food log: checkbox selection + bulk delete ----------
  const foodLogEl = document.getElementById("foodLog");
  const deleteSelectedBtn = document.getElementById("deleteSelectedBtn");

  function updateDeleteSelectedBtn() {
    if (!deleteSelectedBtn) return;
    const checked = document.querySelectorAll(".food-select-cb:checked");
    deleteSelectedBtn.style.display = checked.length > 0 ? "block" : "none";
  }

  if (foodLogEl && !(typeof IS_GUEST !== 'undefined' && IS_GUEST)) {
    // Individual 🗑️ button deletes
    foodLogEl.addEventListener("click", async (e) => {
      const btn = e.target.closest(".delete-food-btn");
      if (!btn) return;
      const logId = btn.getAttribute("data-log-id");
      const li = btn.closest("li[data-log-id]");
      const span = li ? li.querySelector("span") : null;
      const name = (span ? span.textContent : "").split("—")[0].trim();
      if (!confirm(`Delete "${name}" from today's log?`)) return;
      try {
        const res = await fetch(`/api/food-log/${logId}/`, { method: "DELETE" });
        if (res.ok) {
          showToast(`${name} removed from log.`);
          location.reload();
        } else {
          showToast("Failed to delete item.");
        }
      } catch (e) {
        showToast("Network error. Try again.");
      }
    });

    // Checkbox change → show/hide "Delete Selected" button
    foodLogEl.addEventListener("change", (e) => {
      if (e.target.classList.contains("food-select-cb")) updateDeleteSelectedBtn();
    });
  }

  // Bulk delete
  if (deleteSelectedBtn) {
    deleteSelectedBtn.addEventListener("click", async () => {
      const checked = document.querySelectorAll(".food-select-cb:checked");
      if (!checked.length) return;
      const ids = Array.from(checked).map(cb => parseInt(cb.getAttribute("data-log-id")));
      if (!confirm(`Delete ${ids.length} selected item(s)?`)) return;
      try {
        const res = await fetch("/api/food-log/bulk-delete/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ids }),
        });
        if (res.ok) {
          showToast(`${ids.length} item(s) removed.`);
          location.reload();
        } else {
          showToast("Failed to delete items.");
        }
      } catch (e) {
        showToast("Network error. Try again.");
      }
    });
  }

  // ---------- Weight chart ----------
  if (weightData.history && weightData.history.length > 0) {
    const weightCanvas = document.getElementById("weightChart");
    const weightCtx = weightCanvas.getContext("2d");
    const wWidth = weightCanvas.width;
    const wHeight = weightCanvas.height;
    const padding = 40;
    const weights = weightData.history.map(w => w.weight).reverse();
    const dates = weightData.history.map(w => w.date).reverse();

    if (weights.length === 1) {
      weightCtx.fillStyle = "#b084f7";
      weightCtx.beginPath();
      weightCtx.arc(wWidth / 2, wHeight / 2, 6, 0, Math.PI * 2);
      weightCtx.fill();
    } else {
      const maxWeight = Math.max(...weights) + 2;
      const minWeight = Math.min(...weights) - 2;
      const range = maxWeight - minWeight || 1;

      // Axes
      weightCtx.strokeStyle = "rgba(255,255,255,0.3)";
      weightCtx.lineWidth = 2;
      weightCtx.beginPath();
      weightCtx.moveTo(padding, padding);
      weightCtx.lineTo(padding, wHeight - padding);
      weightCtx.lineTo(wWidth - padding, wHeight - padding);
      weightCtx.stroke();

      // Pass 1 — line
      weightCtx.strokeStyle = "#b084f7";
      weightCtx.lineWidth = 3;
      weightCtx.beginPath();
      weights.forEach((weight, i) => {
        const x = padding + ((wWidth - 2 * padding) / (weights.length - 1)) * i;
        const y = wHeight - padding - ((weight - minWeight) / range) * (wHeight - 2 * padding);
        i === 0 ? weightCtx.moveTo(x, y) : weightCtx.lineTo(x, y);
      });
      weightCtx.stroke();

      // Pass 2 — dots
      weights.forEach((weight, i) => {
        const x = padding + ((wWidth - 2 * padding) / (weights.length - 1)) * i;
        const y = wHeight - padding - ((weight - minWeight) / range) * (wHeight - 2 * padding);
        weightCtx.fillStyle = "#fff";
        weightCtx.beginPath();
        weightCtx.arc(x, y, 4, 0, Math.PI * 2);
        weightCtx.fill();
      });

      // Labels
      weightCtx.fillStyle = "rgba(255,255,255,0.7)";
      weightCtx.font = "12px Arial";
      weightCtx.textAlign = "right";
      weightCtx.fillText(`${maxWeight.toFixed(0)}kg`, padding - 5, padding + 5);
      weightCtx.fillText(`${minWeight.toFixed(0)}kg`, padding - 5, wHeight - padding + 5);

      const tooltip = document.createElement("div");
      tooltip.style.cssText = `
          position: absolute; background: rgba(26,8,37,0.95);
          border: 1px solid #8e44ad; border-radius: 8px;
          padding: 6px 12px; color: #d8b4ff; font-size: 13px;
          pointer-events: none; display: none; z-index: 10;
          font-family: 'Poppins', sans-serif;
      `;
      document.body.appendChild(tooltip);

      const dotPositions = weights.map((weight, i) => ({
          x: padding + ((wWidth - 2 * padding) / (weights.length - 1)) * i,
          y: wHeight - padding - ((weight - minWeight) / range) * (wHeight - 2 * padding),
          weight,
          date: dates[i]
      }));

      weightCanvas.addEventListener("mousemove", (e) => {
          const rect = weightCanvas.getBoundingClientRect();
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;

          // Scale for canvas vs display size
          const scaleX = wWidth / rect.width;
          const scaleY = wHeight / rect.height;
          const canvasX = mouseX * scaleX;
          const canvasY = mouseY * scaleY;

          let found = false;
          for (const dot of dotPositions) {
              const dist = Math.sqrt((canvasX - dot.x) ** 2 + (canvasY - dot.y) ** 2);
              if (dist < 12) {
                  tooltip.style.display = "block";
                  tooltip.style.left = `${e.clientX + 12}px`;
                  tooltip.style.top = `${e.clientY - 10}px`;
                  tooltip.innerHTML = `<strong>${dot.weight}kg</strong><br><span style="color:#9b7acf;font-size:11px;">${dot.date}</span>`;
                  found = true;
                  break;
              }
          }
          if (!found) tooltip.style.display = "none";
      });

      weightCanvas.addEventListener("mouseleave", () => {
          tooltip.style.display = "none";
      });
    }
  }


  // ---------- Overlays ----------
  const macroOverlay = document.getElementById("macroOverlay");
  const calOverlay = document.getElementById("calOverlay");
  const scanOverlay = document.getElementById("scanOverlay");
  const weightOverlay = document.getElementById("weightOverlay");

  canvas.addEventListener("click", () => {
    macroOverlay.classList.add("show");
    document.getElementById("macroGrams").innerHTML = Object.entries(macros)
      .map(([k, v]) => `<p><strong>${k}:</strong> ${v}g</p>`).join("");
    document.getElementById("microList").innerHTML = Object.entries(chartData.micros)
      .map(([k, v]) => `<li><strong>${k}:</strong> ${v}mg</li>`).join("");
  });

  document.querySelector(".bar-container").addEventListener("click", () => {
    calOverlay.classList.add("show");
    const rem = Math.round(goal - eaten);
    const calDetailsEl = document.getElementById("calDetails");
    calDetailsEl.textContent = "";
    const line1 = document.createElement("span");
    line1.innerHTML = `You've consumed <strong>${Math.round(eaten)} calories</strong><br>` +
      `out of your <strong>${goal} calorie</strong> goal today.`;
    const br = document.createElement("br");
    const line2 = document.createElement("strong");
    line2.textContent = rem >= 0
      ? `✅ ${rem} kcal remaining`
      : `⚠️ ${Math.abs(rem)} kcal over goal`;
    line2.style.color = rem >= 0 ? "#4caf7d" : "#ff6b6b";
    calDetailsEl.appendChild(line1);
    calDetailsEl.appendChild(br);
    calDetailsEl.appendChild(line2);
  });

  const video = document.getElementById("camera");
  const captureBtn = document.getElementById("captureBtn");
  const scanResult = document.getElementById("scanResult");

  // Bottom nav + button opens the scan/log food overlay
  const bottomNavAdd = document.getElementById("bottomNavAdd");
  if (bottomNavAdd) {
    bottomNavAdd.addEventListener("click", () => {
      scanOverlay.classList.add("show");
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
          .then(stream => { video.srcObject = stream; })
          .catch(err => {
            console.error("Camera denied:", err);
            if (scanResult) scanResult.textContent = "Camera not available.";
          });
      }
    });
  }

  document.getElementById("logWeightBtn")?.addEventListener("click", () => {
    weightOverlay.classList.add("show");
    // Set unit toggle to user's preference
    const savedUnit = (typeof WEIGHT_UNIT !== 'undefined') ? WEIGHT_UNIT : 'kg';
    setWeightUnit(savedUnit);
  });

  // ---------- Weight unit toggle ----------
  let currentWeightUnit = (typeof WEIGHT_UNIT !== 'undefined') ? WEIGHT_UNIT : 'kg';

  function setWeightUnit(unit) {
    currentWeightUnit = unit;
    const kgBtn = document.getElementById("unitKgBtn");
    const lbsBtn = document.getElementById("unitLbsBtn");
    const label = document.getElementById("weightInputLabel");
    const input = document.getElementById("weightInput");
    if (unit === 'kg') {
      kgBtn && kgBtn.classList.add("active");
      lbsBtn && lbsBtn.classList.remove("active");
      if (label) label.textContent = "Weight (kg):";
      if (input) input.placeholder = "70.5";
    } else {
      lbsBtn && lbsBtn.classList.add("active");
      kgBtn && kgBtn.classList.remove("active");
      if (label) label.textContent = "Weight (lbs):";
      if (input) input.placeholder = "155";
    }
  }

  document.getElementById("unitKgBtn")?.addEventListener("click", () => setWeightUnit('kg'));
  document.getElementById("unitLbsBtn")?.addEventListener("click", () => setWeightUnit('lbs'));

  document.getElementById("saveWeightBtn").addEventListener("click", async () => {
    const weight = parseFloat(document.getElementById("weightInput").value);
    const maxVal = currentWeightUnit === 'lbs' ? 1100 : 500;
    if (!weight || weight <= 0 || weight > maxVal) {
      alert(`Enter a valid weight in ${currentWeightUnit}.`);
      return;
    }
    try {
      const res = await fetch("/api/weight-log/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weight, unit: currentWeightUnit }),
      });
      if (!res.ok) { alert("Failed to save weight."); return; }
      location.reload();
    } catch (error) {
      alert("Error logging weight.");
    }
  });

  captureBtn.addEventListener("click", async () => {
    const cap = document.createElement("canvas");
    cap.width = video.videoWidth;
    cap.height = video.videoHeight;
    cap.getContext("2d").drawImage(video, 0, 0, cap.width, cap.height);
    const blob = await new Promise(resolve => cap.toBlob(resolve, "image/jpeg"));
    const formData = new FormData();
    formData.append("image", blob);
    scanResult.textContent = "Scanning...";
    try {
      const response = await fetch("/api/upload-barcode/", {
        method: "POST", body: formData,
      });
      if (!response.ok) throw new Error("Server error");
      const data = await response.json();
      if (data.barcode) {
        const foodData = data.barcode;
        document.getElementById("logSection").style.display = "block";
        document.getElementById("logFoodBtn").onclick = async () => {
          const grams = parseFloat(document.getElementById("gramsInput").value);
          if (!grams || grams <= 0) { alert("Enter valid grams."); return; }
          await logFoodToServer(foodData, grams);
        };
        scanResult.innerHTML = `
          <strong>${foodData.name || "Unknown"}</strong><br>
          Calories: ${foodData.nutrients?.calories_kcal || "?"} kcal/100g
        `;
      } else {
        scanResult.textContent = data.error || "No barcode found.";
        document.getElementById("logSection").style.display = "none";
      }
    } catch (err) {
      scanResult.textContent = "Scan failed. Try again.";
    }
  });

  document.querySelectorAll(".overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("show");
        if (video && video.srcObject) {
          video.srcObject.getTracks().forEach(t => t.stop());
          video.srcObject = null;
        }
      }
    });
  });

  // ---------- Exercise Logging ----------
  const exerciseSelect = document.getElementById("exerciseSelect");
  const exerciseCustomName = document.getElementById("exerciseCustomName");

  exerciseSelect?.addEventListener("change", () => {
    if (exerciseCustomName) {
      exerciseCustomName.style.display = exerciseSelect.value === "__custom__" ? "block" : "none";
    }
  });

  async function handleDeleteExercise(e) {
    const btn = e.currentTarget;
    const id = btn.dataset.exerciseId;
    const li = btn.closest("li");
    const calories = parseFloat(li?.dataset.calories || 0);
    try {
      const res = await fetch(`/api/exercise-log/${id}/`, { method: "DELETE" });
      if (res.ok) {
        if (li) li.remove();
        // Update calorie display
        const calDisplay = document.getElementById("exerciseCalDisplay");
        if (calDisplay && calories) {
          const current = parseFloat(calDisplay.textContent) || 0;
          calDisplay.textContent = Math.max(0, Math.round(current - calories));
        }
      }
    } catch (err) { /* ignore */ }
  }

  document.querySelectorAll(".delete-exercise-btn").forEach(btn => {
    btn.addEventListener("click", handleDeleteExercise);
  });

  document.getElementById("saveExerciseBtn")?.addEventListener("click", async () => {
    const rawName = exerciseSelect && exerciseSelect.value === "__custom__"
      ? (exerciseCustomName ? exerciseCustomName.value.trim() : "")
      : (exerciseSelect ? exerciseSelect.value : "");
    const duration = parseFloat(document.getElementById("exerciseDuration")?.value);
    const notes = document.getElementById("exerciseNotes")?.value.trim() || "";
    const resultEl = document.getElementById("exerciseResult");

    if (!rawName) { if (resultEl) resultEl.textContent = "Please select or enter an exercise."; return; }
    if (!duration || duration <= 0) { if (resultEl) resultEl.textContent = "Please enter a valid duration."; return; }

    try {
      const res = await fetch("/api/exercise-log/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ exercise_name: rawName, duration_minutes: duration, notes }),
      });
      const data = await res.json();
      if (res.ok) {
        if (resultEl) resultEl.textContent = `✅ Logged! ~${data.calories_burned} kcal burned.`;
        // Update the displayed total
        const calDisplay = document.getElementById("exerciseCalDisplay");
        if (calDisplay) {
          const current = parseFloat(calDisplay.textContent) || 0;
          calDisplay.textContent = Math.round(current + data.calories_burned);
        }
        // Add entry to the exercise list
        const list = document.getElementById("exerciseLogList");
        const emptyMsg = list?.querySelector("li:not([data-exercise-id])");
        if (emptyMsg) emptyMsg.remove();
        if (list) {
          const li = document.createElement("li");
          li.className = "food-log-item";
          li.dataset.exerciseId = data.id;
          li.dataset.calories = data.calories_burned;
          li.style.cssText = "display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(155,89,182,0.15);";
          li.innerHTML = `<span style="color:#d8b4ff;font-size:13px;">${data.exercise_name} — ${Math.round(data.duration_minutes)} min — ${data.calories_burned} kcal</span><button class="delete-exercise-btn" data-exercise-id="${data.id}" title="Delete" style="background:none;border:none;cursor:pointer;font-size:15px;">🗑️</button>`;
          list.appendChild(li);
          li.querySelector(".delete-exercise-btn").addEventListener("click", handleDeleteExercise);
        }
        // Reset form
        if (exerciseSelect) exerciseSelect.value = "";
        if (exerciseCustomName) { exerciseCustomName.style.display = "none"; exerciseCustomName.value = ""; }
        const durInput = document.getElementById("exerciseDuration");
        if (durInput) durInput.value = "";
        const notesInput = document.getElementById("exerciseNotes");
        if (notesInput) notesInput.value = "";
      } else {
        if (resultEl) resultEl.textContent = data.error || "Failed to log exercise.";
      }
    } catch (err) {
      if (resultEl) resultEl.textContent = "Error saving exercise.";
    }
  });
});


