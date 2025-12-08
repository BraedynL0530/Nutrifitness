document.addEventListener("DOMContentLoaded", () => {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");

      // Remove active from all
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      // Add active to clicked
      btn.classList.add("active");
      document.getElementById(`${targetTab}-tab`).classList.add("active");
    });
  });

  // ---------- Load data from Django template ----------
  const chartData = JSON.parse(document.getElementById("chart-data").textContent);
  const weightData = JSON.parse(document.getElementById("weight-data").textContent);

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

  setTimeout(() => {
    document.getElementById("bar-fill").style.width = percent + "%";
  }, 100);

  document.getElementById("calorieText").innerText = `${eaten} / ${goal} kcal`;

  // ---------- Weight History Chart ----------
  if (weightData.history && weightData.history.length > 0) {
    const weightCanvas = document.getElementById("weightChart");
    const weightCtx = weightCanvas.getContext("2d");

    const weights = weightData.history.map(w => w.weight);
    const dates = weightData.history.map(w => w.date);

    const maxWeight = Math.max(...weights) + 2;
    const minWeight = Math.min(...weights) - 2;
    const range = maxWeight - minWeight;

    const width = weightCanvas.width;
    const height = weightCanvas.height;
    const padding = 40;

    // Draw axes
    weightCtx.strokeStyle = "rgba(255, 255, 255, 0.3)";
    weightCtx.lineWidth = 2;
    weightCtx.beginPath();
    weightCtx.moveTo(padding, padding);
    weightCtx.lineTo(padding, height - padding);
    weightCtx.lineTo(width - padding, height - padding);
    weightCtx.stroke();

    // Draw line
    weightCtx.strokeStyle = "#b084f7";
    weightCtx.lineWidth = 3;
    weightCtx.beginPath();

    weights.forEach((weight, i) => {
      const x = padding + ((width - 2 * padding) / (weights.length - 1)) * i;
      const y = height - padding - ((weight - minWeight) / range) * (height - 2 * padding);

      if (i === 0) {
        weightCtx.moveTo(x, y);
      } else {
        weightCtx.lineTo(x, y);
      }

      // Draw points
      weightCtx.fillStyle = "#fff";
      weightCtx.beginPath();
      weightCtx.arc(x, y, 4, 0, Math.PI * 2);
      weightCtx.fill();
    });

    weightCtx.stroke();

    // Add labels
    weightCtx.fillStyle = "rgba(255, 255, 255, 0.7)";
    weightCtx.font = "12px Arial";
    weightCtx.textAlign = "right";
    weightCtx.fillText(`${maxWeight.toFixed(0)}kg`, padding - 5, padding + 5);
    weightCtx.fillText(`${minWeight.toFixed(0)}kg`, padding - 5, height - padding + 5);
  }

  // ---------- Overlay controls ----------
  const macroOverlay = document.getElementById("macroOverlay");
  const calOverlay = document.getElementById("calOverlay");
  const scanOverlay = document.getElementById("scanOverlay");
  const weightOverlay = document.getElementById("weightOverlay");

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

  // ---------- Plus button click - show scan overlay ----------
  document.getElementById("plusButton").addEventListener("click", () => {
    scanOverlay.classList.add("show");
  });

  // ---------- Log weight button click ----------
  const logWeightBtn = document.getElementById("logWeightBtn");
  if (logWeightBtn) {
    logWeightBtn.addEventListener("click", () => {
      weightOverlay.classList.add("show");
    });
  }

  // ---------- Save weight ----------
  document.getElementById("saveWeightBtn").addEventListener("click", async () => {
    const weight = parseFloat(document.getElementById("weightInput").value);

    if (!weight || weight <= 0) {
      alert("Enter a valid weight.");
      return;
    }

    try {
      const res = await fetch("/api/weight-log/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weight: weight }),
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("Server error:", errorText);
        alert("Failed to save weight.");
        return;
      }

      alert("Weight logged! Refreshing...");
      location.reload();

    } catch (error) {
      console.error("Error logging weight:", error);
      alert("Error logging weight.");
    }
  });

  // ---------- Barcode scanner ----------
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

  // ---------- Capture and send to backend ----------
  captureBtn.addEventListener("click", async () => {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg"));
    const formData = new FormData();
    formData.append("image", blob);

    scanResult.textContent = "Scanning...";

    try {
      const response = await fetch("/api/upload-barcode/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let text = await response.text();
        console.error("Server error:", text);
        throw new Error("Server returned error");
      }

      let data = await response.json();
      console.log("RAW DATA:", data);

      if (data.barcode) {
        const foodData = data.barcode;

        // Show the log section
        document.getElementById("logSection").style.display = "block";

        // Attach click handler to log button
        document.getElementById("logFoodBtn").onclick = () => logFood(foodData);

        scanResult.innerHTML = `
          <strong>${foodData.name || "Unknown item"}</strong><br>
          Brand: ${foodData.brand || "N/A"}<br>
          Calories: ${foodData.nutrients?.calories_kcal || "?"} kcal per 100g
        `;
      } else {
        scanResult.textContent = data.error || "No barcode found.";
        document.getElementById("logSection").style.display = "none";
      }
    } catch (error) {
      console.error("Scan error:", error);
      scanResult.textContent = "Scan failed. Try again.";
      document.getElementById("logSection").style.display = "none";
    }
  });

  // ---------- Log food function ----------
  async function logFood(food) {
    const grams = parseFloat(document.getElementById("gramsInput").value);

    if (!grams || grams <= 0) {
      alert("Enter valid grams.");
      return;
    }

    // Simple payload - matches what utils.py returns
    const payload = {
      barcode: food.barcode || "unknown",
      name: food.name,
      grams: grams,
      nutrients: food.nutrients,
      micronutrients: food.micronutrients
    };

    console.log("Sending payload:", payload);

    try {
      const res = await fetch("/api/food-log/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("Server error:", errorText);
        alert("Failed to save food.");
        return;
      }

      alert("Food logged! Refresh to see updated totals.");

      //reload to update charts
      location.reload();

    } catch (error) {
      console.error("Error logging food:", error);
      alert("Error logging food.");
    }
  }

  // ---------- Close overlays ----------
  document.querySelectorAll(".overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("show");
      }
    });
  });
});