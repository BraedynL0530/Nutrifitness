document.addEventListener("DOMContentLoaded", () => {
  // ---------- Load data from Django template ----------
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

  // ---------- Animate bar fill after page load ----------
  setTimeout(() => {
    document.getElementById("bar-fill").style.width = percent + "%";
  }, 100);

  document.getElementById("calorieText").innerText = `${eaten} / ${goal} kcal`;

  // ---------- Overlay controls ----------
  const macroOverlay = document.getElementById("macroOverlay");
  const calOverlay = document.getElementById("calOverlay");
  const scanOverlay = document.getElementById("scanOverlay");

  // ---------- Semicircle click - show macros and micros ----------
  canvas.addEventListener("click", () => {
    macroOverlay.classList.add("show");
    document.getElementById("macroGrams").innerHTML = Object.entries(macros)
      .map(([k, v]) => `<p><strong>${k}:</strong> ${v}g</p>`)
      .join("");
    document.getElementById("microList").innerHTML = Object.entries(chartData.micros)
      .map(([k, v]) => `<li><strong>${k}:</strong> ${v}mg</li>`)
      .join("");
  });

  // ---------- Bar click - show calories ----------
  document.querySelector(".bar-container").addEventListener("click", () => {
    calOverlay.classList.add("show");
    document.getElementById("calDetails").innerHTML =
      `You've consumed <strong>${eaten} calories</strong><br>out of your <strong>${goal} calorie</strong> goal today.`;
  });

  // ---------- Plus button click - show scan overlay with zoom animation ----------
  document.getElementById("plusButton").addEventListener("click", () => {
    scanOverlay.classList.add("show");
  });

  // ---------- Barcode scanner(takes a picture and sends it to backend) ----------
  const video = document.getElementById("camera");
  const captureBtn = document.getElementById("captureBtn");
  const scanResult = document.getElementById("scanResult");

  // ---------- Start webcam feed ----------
  if (navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        video.srcObject = stream;
      })
      .catch(err => {
        console.error("Camera access denied:", err);
        scanResult.textContent = "Camera not available.";
      });
  }

  // ---------- Capture a frame and send to Django backend ----------
  captureBtn.addEventListener("click", async () => {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg"));
    const formData = new FormData();
    formData.append("image", blob);

    scanResult.textContent = "Scanning...";

    const response = await fetch("/api/upload-barcode/", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (data.barcode) {
      scanResult.innerHTML = `✅ Barcode: ${data.barcode}<br>Fetching food info...`;
      const foodRes = await fetch(`/api/barcode-data/${data.barcode}/`);
      const foodData = await foodRes.json();

      scanResult.innerHTML = `
        <strong>${foodData.name || "Unknown item"}</strong><br>
        Brand: ${foodData.brand || "N/A"}<br>
        Calories: ${foodData.nutrients?.calories_kcal || "?"} kcal
      `;
    } else {
      scanResult.textContent = data.error || "No barcode found.";
    }
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