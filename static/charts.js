// ---------- PIE CHART (MACROS) ----------
const canvas = document.getElementById("macroChart");
const ctx = canvas.getContext("2d");

const macros = chartData.macros;
const micros = chartData.micros;
let showingMicros = false;

function drawPie(data, colors) {
  const values = Object.values(data);
  const total = values.reduce((a, b) => a + b, 0);
  let startAngle = 0;
  const radius = 120;

  Object.keys(data).forEach((key, i) => {
    const sliceAngle = (values[i] / total) * 2 * Math.PI;

    ctx.beginPath();
    ctx.moveTo(150, 150);
    ctx.arc(150, 150, radius, startAngle, startAngle + sliceAngle);
    ctx.closePath();
    ctx.fillStyle = colors[i % colors.length];
    ctx.fill();

    startAngle += sliceAngle;
  });
}

// Initial draw (macros)
const macroColors = ["#a66df5", "#5e3aa8", "#8c70c4"];
const microColors = ["#b084f7", "#9d6bf2", "#d3a5ff", "#7340b3"];
drawPie(macros, macroColors);

// Click animation for zoom-in (micros)
document.getElementById("plusButton").addEventListener("click", () => {
  if (showingMicros) {
    ctx.clearRect(0, 0, 300, 300);
    drawPie(macros, macroColors);
    showingMicros = false;
  } else {
    // Zoom animation
    let scale = 1;
    const zoom = setInterval(() => {
      ctx.clearRect(0, 0, 300, 300);
      ctx.save();
      ctx.translate(150, 150);
      ctx.scale(scale, scale);
      ctx.translate(-150, -150);
      drawPie(micros, microColors);
      ctx.restore();
      scale += 0.05;
      if (scale >= 1.3) {
        clearInterval(zoom);
        showingMicros = true;
      }
    }, 30);
  }
});

// ---------- BAR CHART (CALORIES) ----------
const goal = chartData.goal_calories;
const eaten = chartData.eaten_calories;

const percent = Math.min((eaten / goal) * 100, 100);
document.getElementById("bar-fill").style.width = percent + "%";
document.getElementById("calorieText").innerText = `${eaten} / ${goal} kcal`;