document.addEventListener("DOMContentLoaded", () => {
    const questions = document.querySelectorAll(".question-card");
    const nextBtn = document.getElementById("next-btn");
    let currentQuestion = 0;
    const data = { allergies: [] };

    function showQuestion(index) {
        questions.forEach((q, i) => q.style.display = i === index ? "block" : "none");
        if (index === questions.length - 1) nextBtn.textContent = "Submit";
    }

    // Handle button selections
    document.querySelectorAll(".sex-option, .activity-option, .diet-option").forEach(btn => {
        btn.addEventListener("click", () => {
            const type = btn.classList.contains("sex-option") ? "sex"
                        : btn.classList.contains("activity-option") ? "activity_level"
                        : "diet";

            document.querySelectorAll(`.${btn.classList[0]}`).forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            data[type] = btn.dataset.value;
        });
    });

    // Handle allergy multi-select
    document.querySelectorAll(".allergy-option").forEach(btn => {
        btn.addEventListener("click", () => {
            btn.classList.toggle("selected");
            const value = btn.dataset.value;
            if (btn.classList.contains("selected")) {
                data.allergies.push(value);
            } else {
                data.allergies = data.allergies.filter(a => a !== value);
            }
        });
    });

    nextBtn.addEventListener("click", async () => {
        // Store text inputs
        data.height = document.getElementById("height")?.value;
        data.weight = document.getElementById("weight")?.value;
        data.bench = document.getElementById("bench")?.value;
        data.squat = document.getElementById("squat")?.value;
        data.deadlift = document.getElementById("deadlift")?.value;

        if (currentQuestion < questions.length - 1) {
            currentQuestion++;
            showQuestion(currentQuestion);
        } else {
            //  submit
            try {
                const res = await fetch("/questionnaire-post", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                    body: JSON.stringify(data),
                });
                const result = await res.json();
                console.log("Submitted:", result);
                //window.location.href = "dashboard"; // Redirect
            } catch (err) {
                console.error(err);
            }
        }
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    showQuestion(currentQuestion);
});
