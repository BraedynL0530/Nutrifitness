document.addEventListener("DOMContentLoaded", () => {
  // Load data from Django template
  const chartData = JSON.parse(document.getElementById("chart-data").textContent);

  // ---------- Semicircle (macros) ----------
  const canvas = document.getElementById("macroChart");
  const ctx = canvas.getContext("2d");
  const macros = chartData.macros;

  const total = Object.values(macros).reduce((a, b) => a + b, 0);
  let start = Math.PI;
  const colors = ["#b084f7", "#8e44ad", "#6c3d99"];
  const centerX = 160;
  const centerY = 140;
  const radius = 90;

  Object.entries(macros).forEach(([name, value], i) => {
    const angle = (value / total) * Math.PI;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, start, start + angle);
    ctx.lineWidth = 30;
    ctx.strokeStyle = colors[i];
    ctx.stroke();
    start += angle;
  });

  // ---------- Bar chart (calories) ----------
  const goal = chartData.goal_calories;
  const eaten = chartData.eaten_calories;
  const percent = Math.min((eaten / goal) * 100, 100);

  // Animate bar fill after page load
  setTimeout(() => {
    document.getElementById("bar-fill").style.width = percent + "%";
  }, 100);

  document.getElementById("calorieText").innerText = `${eaten} / ${goal} kcal`;

  // ---------- Overlay controls ----------
  const macroOverlay = document.getElementById("macroOverlay");
  const calOverlay = document.getElementById("calOverlay");
  const scanOverlay = document.getElementById("scanOverlay");

  // Semicircle click - show macros and micros
  canvas.addEventListener("click", () => {
    macroOverlay.classList.add("show");
    document.getElementById("macroGrams").innerHTML = Object.entries(macros)
      .map(([k, v]) => `<p><strong>${k}:</strong> ${v}g</p>`)
      .join("");
    document.getElementById("microList").innerHTML = Object.entries(chartData.micros)
      .map(([k, v]) => `<li><strong>${k}:</strong> ${v}mg</li>`)
      .join("");
  });

  // Bar click - show calories
  document.querySelector(".bar-container").addEventListener("click", () => {
    calOverlay.classList.add("show");
    document.getElementById("calDetails").innerHTML =
      `You've consumed <strong>${eaten} calories</strong><br>out of your <strong>${goal} calorie</strong> goal today.`;
  });

  // Plus button click - show scan overlay with zoom animation
  document.getElementById("plusButton").addEventListener("click", () => {
    scanOverlay.classList.add("show");
  });

  // ---------- Close overlays when clicking outside ----------
  document.querySelectorAll(".overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("show");
      }
    });
  });
});