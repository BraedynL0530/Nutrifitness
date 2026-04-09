from pyzbar.pyzbar import decode
import os
import requests
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
import joblib
import uuid
import time
from .models import WeeklySummary
load_dotenv()
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
        bmr = 10 * weightKg + 6.25 * heightCm - 5 * int(age) + 5
    else:
        bmr = 10 * weightKg + 6.25 * heightCm - 5 * int(age) - 161
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
            print("Food data found ")
            product = data['product']
            product = simplifyFoodData(product, barcode)
            return product
        else:
            print("No product found.")
    except requests.Timeout:
        print("Request timed out. Try again later.")
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
    return None

def searchFoods(query):
    url = "https://world.openfoodfacts.org/api/v2/search"
    params = {
        "search_terms": query,
        "json": 1,
        "page_size": 8,
        "fields": "product_name,brands,code,nutriments,allergens_tags,categories",
        "cc": "us",  # country code - US products first
        "lc": "en",  # language - English only
        "sort_by": "unique_scans_n"  # most scanned = most popular/relevant
    }
    headers = {
        "User-Agent": "Nutrifitness - Android - Version 1.0 - https://nutrifitness.com",
        "Accept": "application/json"
    }

    for attempt in range(3):
        try:
            res = requests.get(url, params=params, headers=headers, timeout=8)

            if res.status_code == 503:
                print(f"503 on attempt {attempt + 1}, retrying...")
                time.sleep(0.01)
                continue

            if res.status_code != 200:
                print(f"Unexpected status: {res.status_code}")
                return []

            if not res.text.strip():
                return []

            products = res.json().get("products", [])
            results = []
            for p in products:
                if p.get("product_name"):
                    results.append(simplifyFoodData(
                        p, p.get("code", f"search_{uuid.uuid4().hex[:8]}")
                    ))
            return results

        except ValueError as e:
            print(f"JSON parse error: {e}")
            return []
        except Exception as e:
            print(f"Food search error: {e}")
            return []

    print("All 3 attempts failed")
    return searchUSDA(query)

def searchUSDA(query):
    api_key = os.environ.get("USDA_API_KEY")
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "query": query,
        "api_key": api_key,
        "pageSize": 6,
        "dataType": "Branded,SR Legacy"
    }

    try:
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        foods = res.json().get("foods", [])
        results = []
        for f in foods:
            nutrients = {n["nutrientName"]: n["value"]
                        for n in f.get("foodNutrients", [])}
            results.append({
                "name": f.get("description", "Unknown"),
                "brand": f.get("brandOwner", ""),
                "barcode": f.get("gtinUpc") or f"usda_{f.get('fdcId')}",
                "category": f.get("foodCategory", ""),
                "allergens": [],
                "nutrients": {
                    "calories_kcal": nutrients.get("Energy", 0),
                    "proteins_g": nutrients.get("Protein", 0),
                    "fat_g": nutrients.get("Total lipid (fat)", 0),
                    "carbohydrates_g": nutrients.get(
                        "Carbohydrate, by difference", 0
                    ),
                },
                "micronutrients": {
                    "calcium_mg": nutrients.get("Calcium, Ca", 0),
                    "iron_mg": nutrients.get("Iron, Fe", 0),
                    "potassium_mg": nutrients.get("Potassium, K", 0),
                    "magnesium_mg": nutrients.get("Magnesium, Mg", 0),
                    "vitamin-C_mg": nutrients.get(
                        "Vitamin C, total ascorbic acid", 0
                    ),
                    "vitamin-D_mg": nutrients.get("Vitamin D (D2 + D3)", 0),
                }
            })
        return results
    except Exception as e:
        print(f"USDA search error: {e}")
        return []


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
client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))


def generateRecipe(ingredients, allergies, diet):
    if not ingredients:
        return None

    prompt = (
        f"You are a nutrition assistant. Create a healthy recipe with detailed instructions using{', '.join(ingredients)}, "
        f"dietary preferences: {', '.join(diet) if diet else 'none'}, "
        f"avoid allergens: {', '.join(allergies) if allergies else 'none'}. "
        f"Dont use any other ingredients than those specified or common seasonings, you dont have to include all ingredients."
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
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'weight_prediction_model.joblib'
    )
    try:
        model = joblib.load(model_path)
    except:
        return None

    latest_summary = profile.weekly_summary.first()

    if not latest_summary:
        return None

    sex_encoded = 1 if profile.sex == 'male' else 0
    current_weight = profile.get_latest_weight() or profile.weightKg or 70

    features = [
        latest_summary.avg_daily_calories,
        latest_summary.avg_daily_protein,
        sex_encoded,
        profile.tdee,
        current_weight,  # added weight
    ]

    try:
        prediction = model.predict([features])[0]
        return round(float(prediction), 2)
    except Exception as e:
        print(f"Prediction error: {e}")
        return None