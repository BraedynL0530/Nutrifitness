document.addEventListener("DOMContentLoaded", () => {
  // ---------- Load data from Django template ----------
  const chartData = JSON.parse(document.getElementById("pantry-data").textContent);


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
    if (data.barcode) {
      const foodData = data.barcode; // already JSON from backend
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