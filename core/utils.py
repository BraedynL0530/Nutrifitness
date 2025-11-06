import math
from datetime import date
from io import BytesIO #may need may not
import cv2
from pyzbar.pyzbar import decode
import os
import requests
from cerebras.cloud.sdk import Cerebras


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
    try:
        res = requests.get(url, timeout=5)  # <- add timeout here
        res.raise_for_status()
        data = res.json()
        if 'product' in data:
            print("Food data found ✅")
            product = data['product']
            simplifyFoodData(product)
            return product
        else:
            print("No product found.")
    except requests.Timeout:
        print("⚠️ Request timed out. Try again later.")
    except requests.RequestException as e:
        print(f"⚠️ Error fetching data: {e}")
    return None

def simplifyFoodData(product):
    print("SIMPLIFED FOOD DATA:")
    return {
        "name": product.get("product_name", "Unknown"),
        "brand": product.get("brands", "Unknown"),
        "category": product.get("categories", "Unknown"),
        "allergens": product.get("allergens_tags", []),
        "nutrients": {
            "calories_kcal": product.get("nutriments", {}).get("energy-kcal_100g"),
            "fat_g": product.get("nutriments", {}).get("fat_100g"),
            "saturated_fat_g": product.get("nutriments", {}).get("saturated-fat_100g"),
            "carbohydrates_g": product.get("nutriments", {}).get("carbohydrates_100g"),
            "sugars_g": product.get("nutriments", {}).get("sugars_100g"),
            "fiber_g": product.get("nutriments", {}).get("fiber_100g"),
            "proteins_g": product.get("nutriments", {}).get("proteins_100g"),
            "salt_g": product.get("nutriments", {}).get("salt_100g"),
            "sodium_mg": product.get("nutriments", {}).get("sodium_100g"),
        },
        "micronutrients": {
            "calcium_mg": product.get("nutriments", {}).get("calcium_100g"),
            "iron_mg": product.get("nutriments", {}).get("iron_100g"),
            "potassium_mg": product.get("nutriments", {}).get("potassium_100g"),
        },
        "ecoscore_grade": product.get("ecoscore_grade", "Unknown")
    }
#barcode scanner is functional
def generateFitnessPlan(x,y):
    return

client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))
def generateRecipe(ingredients,allergies):
    prompt =  prompt = (f"You are a nutrition assistant. Create a healthy recipe using{','.join(ingredients)}, "
                        f"avoid{','.join(allergies)}. Include calories macro and micronutrients in structured json format.")
    stream = client.chat.completions.create(
        model="cerebras-13b-instruct-v1",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        stream=True,
        temperature=0.7,
        max_tokens=1000,
    )

    result_text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            result_text += delta

    return result_text

#barcodeScanner() testing barcode