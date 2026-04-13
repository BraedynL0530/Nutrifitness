document.addEventListener("DOMContentLoaded", () => {
  // Load pantry items from Django data
  loadPantryItems();

  // Elements
  const scanOverlay = document.getElementById("scanOverlay");
  const video = document.getElementById("camera");
  const captureBtn = document.getElementById("captureBtn");
  const scanResult = document.getElementById("scanResult");

  // Bottom nav + button opens scanner overlay
  const bottomNavAdd = document.getElementById("bottomNavAdd");
  if (bottomNavAdd) {
    bottomNavAdd.addEventListener("click", () => {
      scanOverlay.classList.add("show");
      startCamera();
    });
  }

  // Close overlay when clicking outside
  scanOverlay.addEventListener("click", (e) => {
    if (e.target === scanOverlay) {
      scanOverlay.classList.remove("show");
      stopCamera();
    }
  });

  function startCamera() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => { video.srcObject = stream; })
        .catch(err => {
          console.error("Camera access denied:", err);
          if (scanResult) scanResult.textContent = "Camera not available.";
        });
    }
  }

  function stopCamera() {
    if (video && video.srcObject) {
      video.srcObject.getTracks().forEach(t => t.stop());
      video.srcObject = null;
    }
  }

  // Mode tabs (scan / search)
  function setPantryMode(mode) {
    const scanArea = document.getElementById("pantryScanArea");
    const searchArea = document.getElementById("pantrySearchArea");
    const btnScan = document.getElementById("pantryBtnScan");
    const btnSearch = document.getElementById("pantryBtnSearch");
    if (mode === "scan") {
      if (scanArea) scanArea.style.display = "block";
      if (searchArea) searchArea.style.display = "none";
      btnScan && btnScan.classList.add("active");
      btnSearch && btnSearch.classList.remove("active");
      startCamera();
    } else {
      if (scanArea) scanArea.style.display = "none";
      if (searchArea) searchArea.style.display = "block";
      btnSearch && btnSearch.classList.add("active");
      btnScan && btnScan.classList.remove("active");
      stopCamera();
    }
  }

  document.getElementById("pantryBtnScan")?.addEventListener("click", () => setPantryMode("scan"));
  document.getElementById("pantryBtnSearch")?.addEventListener("click", () => setPantryMode("search"));

  // Pantry search
  async function runPantrySearch() {
    const query = document.getElementById("pantrySearchInput")?.value.trim();
    if (!query) return;
    const container = document.getElementById("pantrySearchResults");
    if (!container) return;
    container.innerHTML = '<p style="color:#9b7acf;">Searching...</p>';
    try {
      const res = await fetch(`/api/food-search/?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      if (!data.results || data.results.length === 0) {
        container.innerHTML = '<p style="color:#9b7acf;">No results found.</p>';
        return;
      }
      container.innerHTML = data.results.map((food, i) => `
        <div style="background:rgba(155,89,182,0.15); border-radius:8px;
                    padding:10px; margin:6px 0; text-align:left;">
          <strong style="color:#d8b4ff;">${food.name || "Unknown"}</strong><br>
          <span style="color:#9b7acf; font-size:13px;">
            ${food.nutrients?.calories_kcal || "?"} kcal |
            P: ${food.nutrients?.proteins_g || "?"}g
          </span><br>
          <button onclick='addSearchedToPantry(${JSON.stringify(food).replace(/'/g, "&#39;")})'
                  style="margin-top:8px; width:100%; padding:7px; background:#8e44ad; border:none;
                         border-radius:6px; color:white; cursor:pointer; font-weight:600;">
            + Add to Pantry
          </button>
        </div>
      `).join("");
    } catch (e) {
      container.innerHTML = '<p style="color:#ff6b6b;">Search failed. Try again.</p>';
    }
  }

  window.runPantrySearch = runPantrySearch;

  window.addSearchedToPantry = async function(food) {
    await addToPantry(food);
  };

  // Capture and scan barcode
  captureBtn && captureBtn.addEventListener("click", async () => {
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
      container.innerHTML = '<p class="empty-message">Your pantry is empty. Scan or search items to add them!</p>';
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

    if (retryBtn) retryBtn.style.display = "none";
    generateBtn.disabled = true;
    generateBtn.textContent = "Generating...";
    resultDiv.innerHTML = '<p style="color: #9b7acf;">🔄 Creating your recipe...</p>';

    try {
      const response = await fetch("/api/pantry-ai/", { method: "GET" });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));

        // Handle ingredient validation failure with a retry prompt
        if (response.status === 422 && errData.needs_regeneration) {
          resultDiv.innerHTML = `
            <p style="color:#f7b731;">⚠️ AI used ingredients not in your pantry. Please try again.</p>
          `;
          generateBtn.textContent = "Try Again";
          generateBtn.disabled = false;
          if (retryBtn) retryBtn.style.display = "inline-block";
          return;
        }

        throw new Error(errData.error || "Failed to generate recipe");
      }

      const data = await response.json();
      const nutrients = data.nutrients || {};
      const recipeName = nutrients.recipe_name || "AI Generated Recipe";

      // Display clean recipe text (JSON already stripped by backend)
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
          <p style="margin-top:12px; font-size:12px; color:rgba(216,180,255,0.5); text-align:center; font-style:italic;">
            ⚠️ AI may make mistakes — always double-check ingredients and portion sizes.
          </p>
        </div>
      `;

      document.getElementById("logRecipeBtn").addEventListener("click", async () => {
        const payload = {
          barcode: `recipe_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          name: recipeName,
          grams: 100,
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
      resultDiv.innerHTML = `<p style="color: #ff6b6b;">${error.message || "Failed to generate recipe. Try again."}</p>`;
      generateBtn.textContent = "Generate Recipe";
      generateBtn.disabled = false;
      if (retryBtn) retryBtn.style.display = "inline-block";
    }
  }

  // Retry button handler
  const retryBtn = document.getElementById("retryRecipeBtn");
  if (retryBtn) {
    retryBtn.addEventListener("click", generateRecipe);
  }
});