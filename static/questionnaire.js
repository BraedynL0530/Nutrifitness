document.addEventListener("DOMContentLoaded", () => {
    const questions = document.querySelectorAll(".question-card");
    const nextBtn = document.getElementById("next-btn");
    let current = 0;

    // Show first question
    questions[current].classList.add("active");

    // Only allow numeric input
    document.querySelectorAll('input[type="number"]').forEach(input => {
        input.addEventListener("input", e => {
            e.target.value = e.target.value.replace(/[^0-9.]/g, "");
        });
    });

    // NEXT button click
    nextBtn.addEventListener("click", () => {
        const currentQ = questions[current];
        const required = currentQ.dataset.required === "true";
        removeWarning(currentQ);

        let answered = false;

        // Numeric inputs
        if (currentQ.querySelector("input")) {
            const inputs = currentQ.querySelectorAll("input");
            answered = [...inputs].some(i => i.value.trim() !== "");
            const invalid = [...inputs].some(i => isNaN(i.value) || i.value.trim() === "");
            if (required && invalid) {
                showWarning(currentQ, "Please enter valid numbers only.");
                return;
            }
        }
        // Sex buttons
        else if (currentQ.querySelector(".sex-option")) {
            answered = !!currentQ.dataset.answer;
        }
        // Activity buttons
        else if (currentQ.querySelector(".activity-option")) {
            answered = !!currentQ.dataset.answer;
        }

        if (required && !answered) {
            showWarning(currentQ, "Please answer this question before continuing.");
            return;
        }

        // Move to next question
        currentQ.classList.remove("active");
        current++;
        if (current < questions.length) {
            questions[current].classList.add("active");
        } else {
            submitData();
        }
    });

    // SEX buttons
    document.querySelectorAll(".sex-option").forEach(btn => {
        btn.addEventListener("click", () => {
            const parent = btn.closest(".question-card");
            parent.dataset.answer = btn.dataset.value;
            parent.querySelectorAll(".sex-option").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
        });
    });

    // ACTIVITY buttons
    document.querySelectorAll(".activity-option").forEach(btn => {
        btn.addEventListener("click", () => {
            const parent = btn.closest(".question-card");
            parent.dataset.answer = btn.dataset.value;
            parent.querySelectorAll(".activity-option").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
        });
    });

    // Warning helpers
    function showWarning(card, message) {
        const warning = document.createElement("div");
        warning.className = "warning";
        warning.textContent = message;
        card.appendChild(warning);
        setTimeout(() => warning.remove(), 3000);
    }

    function removeWarning(card) {
        const warning = card.querySelector(".warning");
        if (warning) warning.remove();
    }

    // Submit data
    function submitData() {
        const sexCard = document.querySelector(".sex-option.selected")?.closest(".question-card");
        const activityCard = document.querySelector(".activity-option.selected")?.closest(".question-card");

        const data = {
            sex: sexCard?.dataset.answer,
            height: document.getElementById("height").value,
            weight: document.getElementById("weight").value,
            bench: document.getElementById("bench").value,
            squat: document.getElementById("squat").value,
            deadlift: document.getElementById("deadlift").value,
            activity_level: activityCard?.dataset.answer
        };

        // Validate required numeric fields before sending
        const requiredNums = ['height', 'weight'];
        for (let field of requiredNums) {
            if (!data[field] || isNaN(data[field])) {
                showWarning(document.body, `Invalid value for ${field}`);
                return;
            }
        }

        fetch("/questionnaire-post", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        })
        .then(res => {
            if (res.ok) showSuccess();
            else throw new Error("Failed to submit");
        })
        .catch(() => showWarning(document.body, "Submission failed. Try again."));
    }

    // Success overlay
    function showSuccess() {
        const overlay = document.createElement("div");
        overlay.className = "overlay-success";
        overlay.innerHTML = "<h2>Submitted successfully!</h2>";
        document.body.appendChild(overlay);
        setTimeout(() => overlay.remove(), 2000);
    }
});
