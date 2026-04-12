document.addEventListener("DOMContentLoaded", () => {
  // Load pantry items from Django data
  loadPantryItems();

  // Elements
  const scanButton = document.getElementById("scanButton");
  const scanOverlay = document.getElementById("scanOverlay");
  const video = document.getElementById("camera");
  const captureBtn = document.getElementById("captureBtn");
  const scanResult = document.getElementById("scanResult");

  // Open scanner overlay
  scanButton.addEventListener("click", () => {
    scanOverlay.classList.add("show");
  });

  // Close overlay when clicking outside
  scanOverlay.addEventListener("click", (e) => {
    if (e.target === scanOverlay) {
      scanOverlay.classList.remove("show");
    }
  });

  // Start webcam
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

  // Capture and scan barcode
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
        throw new Error("Server returned error");
      }

      let data = await response.json();
      console.log("Scanned data:", data);

      if (data.barcode) {
        const foodData = data.barcode;

        scanResult.innerHTML = `
          <strong style="color: #d8b4ff;">${foodData.name || "Unknown item"}</strong><br>
          <span style="color: #9b7acf;">Brand: ${foodData.brand || "N/A"}</span><br>
          <span style="color: #c9b3e8;">Calories: ${foodData.nutrients?.calories_kcal || "?"} kcal per 100g</span><br>
          <button id="addToPantryBtn" class="add-pantry-btn">Add to Pantry</button>
        `;

        document.getElementById("addToPantryBtn").onclick = () => addToPantry(foodData);

      } else {
        scanResult.textContent = data.error || "No barcode found.";
      }
    } catch (error) {
      console.error("Scan error:", error);
      scanResult.textContent = "Scan failed. Try again.";
    }
  });

  // Add item to pantry
  async function addToPantry(food) {
    const payload = {
      barcode: food.barcode || "unknown",
      name: food.name,
      category: food.category,
      allergens: food.allergens,
      nutrients: food.nutrients,
      micronutrients: food.micronutrients
    };

    console.log("Adding to pantry:", payload);

    try {
      const res = await fetch("/api/pantry-log/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("Server error:", errorText);
        alert("Failed to add to pantry.");
        return;
      }

      alert(`${food.name} added to pantry!`);
      location.reload();

    } catch (error) {
      console.error("Error adding to pantry:", error);
      alert("Error adding to pantry.");
    }
  }

  // Load and display pantry items
  function loadPantryItems() {
    const container = document.getElementById("pantryItems");

    if (!pantryData || pantryData.length === 0) {
      container.innerHTML = '<p class="empty-message">Your pantry is empty. Scan items to add them!</p>';
      return;
    }

    container.innerHTML = "";

    pantryData.forEach(item => {
      const card = document.createElement("div");
      card.className = "pantry-item";

      card.innerHTML = `
        <h3 class="pantry-item-name">${item.name}</h3>
        <p class="pantry-item-brand">${item.brand || "Unknown Brand"}</p>
        <p class="pantry-item-info">Category: ${item.category || "N/A"}</p>
        <p class="pantry-item-info">Calories: ${item.calories || 0} kcal per 100g</p>
        <p class="pantry-item-quantity">Quantity: ${item.quantity} ${item.unit || "item"}${item.quantity > 1 ? "s" : ""}</p>
      `;

      container.appendChild(card);
    });
  }

  // Generate recipe button
  const generateBtn = document.getElementById("generateRecipeBtn");
  if (generateBtn) {
    generateBtn.addEventListener("click", generateRecipe);
  }

  // Generate recipe from pantry items
  async function generateRecipe() {
    const resultDiv = document.getElementById("recipeResult");
    const generateBtn = document.getElementById("generateRecipeBtn");
    const retryBtn = document.getElementById("retryRecipeBtn");

    // Hide retry button, show loading
    if (retryBtn) retryBtn.style.display = "none";
    generateBtn.disabled = true;
    generateBtn.textContent = "Generating...";
    resultDiv.innerHTML = '<p style="color: #9b7acf;">🔄 Creating your recipe...</p>';

    try {
      const response = await fetch("/api/pantry-ai/", {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error("Failed to generate recipe");
      }

      const data = await response.json();
      console.log("Recipe data:", data);

      const nutrients = data.nutrients || {};
      const recipeName = nutrients.recipe_name || "AI Generated Recipe";

      // Display recipe with nutrition summary and log button
      resultDiv.innerHTML = `
        <div style="text-align: left; color: #d8b4ff; line-height: 1.6;">
          <pre style="white-space: pre-wrap; font-family: inherit;">${data.recipe}</pre>
          <div style="margin-top: 16px; padding: 14px; background: rgba(155,89,182,0.15); border-radius: 10px; border: 1px solid #9b59b6;">
            <h4 style="color: #d8b4ff; margin: 0 0 10px 0;">📊 Nutrition Summary</h4>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 14px;">
              <span>🔥 Calories: <strong>${nutrients.calories || 0} kcal</strong></span>
              <span>💪 Protein: <strong>${nutrients.protein || 0}g</strong></span>
              <span>🌾 Carbs: <strong>${nutrients.carbs || 0}g</strong></span>
              <span>🥑 Fat: <strong>${nutrients.fat || 0}g</strong></span>
            </div>
            <button id="logRecipeBtn" style="margin-top: 12px; padding: 10px 20px; background: linear-gradient(135deg, #27ae60, #2ecc71); border: none; border-radius: 8px; color: white; font-size: 14px; font-weight: 600; cursor: pointer; width: 100%;">
              🍽️ Log Meal?
            </button>
          </div>
        </div>
      `;

      document.getElementById("logRecipeBtn").addEventListener("click", async () => {
        const payload = {
          barcode: `recipe_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          name: recipeName,
          grams: 100, // quantity = grams/100 = 1 serving; nutrients represent the full recipe
          nutrients: {
            calories_kcal: nutrients.calories || 0,
            proteins_g: nutrients.protein || 0,
            carbohydrates_g: nutrients.carbs || 0,
            fat_g: nutrients.fat || 0,
          },
          micronutrients: {},
          category: "AI Recipe",
          allergens: []
        };

        try {
          const res = await fetch("/api/food-log/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (res.ok) {
            alert(`${recipeName} logged to your food diary!`);
          } else {
            const err = await res.json();
            alert(err.error || "Failed to log meal.");
          }
        } catch (e) {
          alert("Network error. Try again.");
        }
      });

      generateBtn.textContent = "Generate Another Recipe";
      generateBtn.disabled = false;

    } catch (error) {
      console.error("Recipe generation error:", error);
      resultDiv.innerHTML = '<p style="color: #ff6b6b;">Failed to generate recipe. Try again.</p>';
      generateBtn.textContent = "Generate Recipe";
      generateBtn.disabled = false;

      // Show retry button
      if (retryBtn) retryBtn.style.display = "inline-block";
    }
  }

  // Retry button handler
  const retryBtn = document.getElementById("retryRecipeBtn");
  if (retryBtn) {
    retryBtn.addEventListener("click", generateRecipe);
  }
});