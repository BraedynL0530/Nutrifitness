import math
from datetime import date
from io import BytesIO

def calcBmi(weightKg, heightCm):
    heightMeter = heightCm / 100.0
    bmi = weightKg / (heightMeter * heightMeter)
    return round(bmi, 2)

def calcBmiCat(bmi):
    if bmi <18.5:
        return "Underweight"
    elif bmi <25:
        return "Normal"
    elif bmi <30:
        return "Overweight"
    else:
        return "Obese"

def calcBmr(weightKg,heightCm,age, sex):
    if sex == 'male':
        bmr = 10 * weightKg + 6.25 * heightCm - 5 * age + 5
    else:
        bmr = 10 * weightKg + 6.25 * heightCm - 5 * age - 161
    return round(bmr)

lifeStyleFactors = {
    "Sedentary": 1.2,
    "Lightly active": 1.375,
    "Moderately active": 1.55,
    "Very active": 1.725,
    "Extremely active": 1.9,
}

def calcTdee(bmr, activityFactor):
    return round(bmr * activityFactor)

def proteinTarget(weightkg, goal):
    if goal == "gain":
        gPerKg = 1.8
    elif goal == "lose":
        gPerKg = 1.2
    else:
        gPerKg = 1
    grams = round(weightkg * gPerKg)
    return grams