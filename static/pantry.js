document.addEventListener("DOMContentLoaded", () => {
  // ---------- Load data from Django template ----------
  const pantryData = JSON.parse(document.getElementById("pantry-data").textContent);






  // ---------- Overlay controls ----------
  const scanOverlay = document.getElementById("scanOverlay");



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


  if (!response.ok) {
      let text = await response.text()
      console.error("Server error:", text)
      throw new Error("Server returned non-JSON error")
  }

  let data = await response.json()

    console.log("RAW DATA:", data);
    console.log("BARCODE:", data.barcode);
    if (data.barcode) {
      const foodData = data.barcode; // already JSON from backend
      document.getElementById("logSection").style.display = "block";
      document.getElementById("logFoodBtn").onclick = () => logFood(foodData);
      scanResult.innerHTML = `
        <strong>${foodData.name || "Unknown item"}</strong><br>
        Brand: ${foodData.brand || "N/A"}<br>
        Calories: ${foodData.nutrients?.calories_kcal || "?"} kcal
      `;
    } else {
      scanResult.textContent = data.error || "No barcode found.";
    }
  });

  async function logFood(food) {
  if (!grams || grams <= 0) {
    alert("Enter valid grams.");
    return;
  }


  const payload = {
    barcode: food.barcode,
    name: food.name,
    brand: food.brand,
    nutrients_100g: food.nutrients
  };

  const res = await fetch("/api/pantry-log/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    console.error(await res.text());
    alert("Failed to save food.");
    return;
  }

  const data = await res.json();

  // update calories UI
  document.getElementById("calorieText").innerText =
    `${data.eaten_calories} / ${data.goal_calories} kcal`;

  document.getElementById("bar-fill").style.width =
    Math.min((data.eaten_calories / data.goal_calories) * 100, 100) + "%";

  // update macros semicircle numbers
  document.getElementById("macroGrams").innerHTML = `
    <p><strong>Protein:</strong> ${data.nutrients.protein.toFixed(1)}g</p>
    <p><strong>Carbs:</strong> ${data.nutrients.carbs.toFixed(1)}g</p>
    <p><strong>Fat:</strong> ${data.nutrients.fat.toFixed(1)}g</p>
  `;

  // add the new food to list
  addFoodToUI(data.food);

  scanOverlay.classList.remove("show");
  }

  // ---------- Close overlays when clicking outside ----------
  document.querySelectorAll(".overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("show");
      }
    });
  });
});