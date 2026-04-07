function setFoodMode(mode) {
  ["scan", "search", "manual"].forEach(m => {
    document.getElementById(`${m}Mode`).style.display = m === mode ? "block" : "none";
    document.getElementById(`btn-${m}`).classList.toggle("active", m === mode);
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
    container.innerHTML = data.results.map((food, i) => `
      <div style="background:rgba(155,89,182,0.15); border-radius:8px; 
                  padding:10px; margin:6px 0; text-align:left;">
        <strong style="color:#d8b4ff;">${food.name || "Unknown"}</strong><br>
        <span style="color:#9b7acf; font-size:13px;">
          ${food.nutrients?.calories_kcal || "?"} kcal | 
          P: ${food.nutrients?.proteins_g || "?"}g | 
          C: ${food.nutrients?.carbohydrates_g || "?"}g | 
          F: ${food.nutrients?.fat_g || "?"}g
        </span><br>
        <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
          <input type="number" id="sg${i}" value="100" min="1"
                 style="width:65px; padding:5px; border:1px solid #8e44ad; 
                        border-radius:6px; background:rgba(155,89,182,0.1); color:#d8b4ff;">
          <span style="color:#9b7acf; font-size:13px;">g</span>
          <button onclick='logSearchFood(${JSON.stringify(food).replace(/'/g, "&#39;")}, ${i})'
                  style="flex:1; padding:6px; background:#8e44ad; border:none; 
                         border-radius:6px; color:white; cursor:pointer; font-weight:600;">
            Log
          </button>
        </div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = '<p style="color:#ff6b6b;">Search failed. Try again.</p>';
  }
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
  const eaten = chartData.eaten_calories;
  const percent = Math.min((eaten / goal) * 100, 100);
  setTimeout(() => {
    document.getElementById("bar-fill").style.width = percent + "%";
  }, 100);
  document.getElementById("calorieText").innerText = `${eaten} / ${goal} kcal`;

  // ---------- Weight chart ----------
  if (weightData.history && weightData.history.length > 0) {
    const weightCanvas = document.getElementById("weightChart");
    const weightCtx = weightCanvas.getContext("2d");
    const wWidth = weightCanvas.width;
    const wHeight = weightCanvas.height;
    const padding = 40;
    const weights = weightData.history.map(w => w.weight);

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
    }
  } // <-- THIS was the missing brace

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
    document.getElementById("calDetails").innerHTML =
      `You've consumed <strong>${eaten} calories</strong><br>out of your <strong>${goal} calorie</strong> goal today.`;
  });

  const video = document.getElementById("camera");
  const captureBtn = document.getElementById("captureBtn");
  const scanResult = document.getElementById("scanResult");

  document.getElementById("plusButton").addEventListener("click", () => {
    scanOverlay.classList.add("show");
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => { video.srcObject = stream; })
        .catch(err => {
          console.error("Camera denied:", err);
          if (scanResult) scanResult.textContent = "Camera not available.";
        });
    }
  });

  document.getElementById("logWeightBtn")?.addEventListener("click", () => {
    weightOverlay.classList.add("show");
  });

  document.getElementById("saveWeightBtn").addEventListener("click", async () => {
    const weight = parseFloat(document.getElementById("weightInput").value);
    if (!weight || weight <= 0 || weight > 500) {
      alert("Enter a valid weight.");
      return;
    }
    try {
      const res = await fetch("/api/weight-log/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weight }),
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
        if (video.srcObject) {
          video.srcObject.getTracks().forEach(t => t.stop());
          video.srcObject = null;
        }
      }
    });
  });
});