import math
from datetime import date
from io import BytesIO
import cv2
from pyzbar.pyzbar import decode
import requests

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

def barcodeScanner():
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        success, frame = cap.read()
        frame = cv2.flip(frame, 1)
        cv2.imshow('Barcode Scanner', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            barcode = decode(frame)
            if barcode:
                barcode_data = barcode[0].data.decode('utf-8')
                food_info = readFoodData(barcode_data)
                print(food_info)

                cap.release()
                cv2.destroyAllWindows()
                return food_info
            else:
                print("No barcode found")

    cap.release()
    cv2.destroyAllWindows()


def readFoodData(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    res = requests.get(url)
    if res.status_code == 200:
        print("Food data found")
        data = res.json()
        if 'product' in data:
            return data['product']
        else:
            print("No product found.")
    else:
        print("Error fetching data.")

def generateFitnessPlan(x,y):
    return