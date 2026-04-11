function setHeightUnit(unit) {
    const cmInput = document.getElementById("heightCmInput");
    const ftInput = document.getElementById("heightFtInput");
    const cmBtn = document.getElementById("heightCmBtn");
    const ftBtn = document.getElementById("heightFtBtn");

    if (unit === 'cm') {
        cmInput.style.display = "block";
        ftInput.style.display = "none";
        cmBtn.classList.add("active");
        ftBtn.classList.remove("active");
    } else {
        cmInput.style.display = "none";
        ftInput.style.display = "flex";
        cmBtn.classList.remove("active");
        ftBtn.classList.add("active");
    }
}

function setWeightUnit(unit) {
    const kgInput = document.getElementById("weightKgInput");
    const lbInput = document.getElementById("weightLbInput");
    const kgBtn = document.getElementById("weightKgBtn");
    const lbBtn = document.getElementById("weightLbBtn");

    if (unit === 'kg') {
        kgInput.style.display = "block";
        lbInput.style.display = "none";
        kgBtn.classList.add("active");
        lbBtn.classList.remove("active");
    } else {
        kgInput.style.display = "none";
        lbInput.style.display = "block";
        kgBtn.classList.remove("active");
        lbBtn.classList.add("active");
    }
}

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

document.addEventListener("DOMContentLoaded", () => {
    const questions = document.querySelectorAll(".question-card");
    const nextBtn = document.getElementById("next-btn");
    let currentQuestion = 0;
    const data = {allergies: []};

    function showQuestion(index) {
        questions.forEach((q, i) => q.style.display = i === index ? "block" : "none");
        if (index === questions.length - 1) nextBtn.textContent = "Submit";
    }

    // Show first question on page load
    showQuestion(currentQuestion);

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

    document.querySelectorAll(".goal-option").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".goal-option").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            data.goal = btn.dataset.value;
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

    // Handle next/submit button
    nextBtn.addEventListener("click", async () => {
        // Height — convert ft/in to cm if needed
        const usingFt = document.getElementById("heightFtBtn").classList.contains("active");
        if (usingFt) {
            const ft = parseFloat(document.getElementById("heightFt")?.value) || 0;
            const inches = parseFloat(document.getElementById("heightIn")?.value) || 0;
            data.height = ((ft * 12 + inches) * 2.54).toFixed(1);
        } else {
            data.height = document.getElementById("height")?.value;
        }

        // Weight — convert lbs to kg if needed
        const usingLbs = document.getElementById("weightLbBtn").classList.contains("active");
        if (usingLbs) {
            const lbs = parseFloat(document.getElementById("weightLbs")?.value) || 0;
            data.weight = (lbs * 0.453592).toFixed(1);
        } else {
            data.weight = document.getElementById("weight")?.value;
        }
        data.bench = document.getElementById("bench")?.value;
        data.squat = document.getElementById("squat")?.value;
        data.deadlift = document.getElementById("deadlift")?.value;
        data.age = document.getElementById("age")?.value;

        if (currentQuestion < questions.length - 1) {
            currentQuestion++;
            showQuestion(currentQuestion);
        } else {
            // submit
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
                window.location.href = "/"; //redirect
            } catch (err) {
                console.error(err);
            }
        }
    });
});
