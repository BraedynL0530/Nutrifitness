from pyzbar.pyzbar import decode
import os
import requests
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
import joblib


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

def barcodeScanner(frame):
    barcode = decode(frame)
    if not barcode:
        return{"error":"no barcode found"}
    else:
        barcode_data = barcode[0].data.decode('utf-8')
        food_info = readFoodData(barcode_data)
        print(food_info)
        return food_info


def readFoodData(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        res = requests.get(url, timeout=5)  # <- add timeout here
        res.raise_for_status()
        data = res.json()
        if 'product' in data:
            print("Food data found ✅")
            product = data['product']
            product = simplifyFoodData(product, barcode)
            return product
        else:
            print("No product found.")
    except requests.Timeout:
        print("⚠️ Request timed out. Try again later.")
    except requests.RequestException as e:
        print(f"⚠️ Error fetching data: {e}")
    return None

def simplifyFoodData(product,barcode):
    print("SIMPLIFIED FOOD DATA:")
    return {
        "name": product.get("product_name", "Unknown"),
        "brand": product.get("brands", "Unknown"),
        "barcode": barcode,
        "category": product.get("categories", "Unknown"),
        "allergens": product.get("allergens_tags", []),
        "nutrients": {
            "calories_kcal": product.get("nutriments", {}).get("energy-kcal_100g"),
            "fat_g": product.get("nutriments", {}).get("fat_100g"),
            "carbohydrates_g": product.get("nutriments", {}).get("carbohydrates_100g"),
            "proteins_g": product.get("nutriments", {}).get("proteins_100g"),


        },
        "micronutrients": {
            "calcium_mg": product.get("nutriments", {}).get("calcium_100g"),
            "iron_mg": product.get("nutriments", {}).get("iron_100g"),
            "potassium_mg": product.get("nutriments", {}).get("potassium_100g"),
            "magnesium_mg": product.get("nutriments", {}).get("magnesium_100g"),
            "vitamin-C_mg": product.get("nutriments", {}).get("vitamin-C_100g"),
            "vitamin-D_mg": product.get("nutriments", {}).get("vitamin-D_100g"),

        },
        "ecoscore_grade": product.get("ecoscore_grade", "Unknown")
    }
#barcode scanner is functional
def generateFitnessPlan(x,y):
    return


load_dotenv()
client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))


def generateRecipe(ingredients, allergies, diet):
    if not ingredients:
        return None

    prompt = (
        f"You are a nutrition assistant. Create a healthy recipe with detailed instructions using some of {', '.join(ingredients)}, "
        f"dietary preferences: {', '.join(diet) if diet else 'none'}, "
        f"avoid allergens: {', '.join(allergies) if allergies else 'none'}. "
        f"Include calories, macros, and micronutrients in structured JSON format.")
    stream = client.chat.completions.create(
        model="llama3.1-8b", # Dudes changed the model since i last added this i was wondering the issue may experiment with models
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


def getWeightPrediction(profile):

    try:
        model = joblib.load('weight_prediction_model.joblib')
    except:
        return None

    # Get most recent week's data
    latest_summary = profile.weekly_summaries.first()

    if not latest_summary:
        # No data yet - need to create summaries first
        return None

    sex_encoded = 1 if profile.sex == 'male' else 0

    features = [
        latest_summary.avg_daily_calories,
        latest_summary.avg_daily_protein,
        sex_encoded,
        profile.tdee,
    ]

    # Predict
    try:
        prediction = model.predict([features])[0]
        return prediction
    except Exception as e:
        print(f"Prediction error: {e}")
        return None