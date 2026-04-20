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
    off_user = os.environ.get("OFF_API_USER", "")
    off_pass = os.environ.get("OFF_API_PASS", "")
    user_agent = "Nutrifitness - Mobile App - Version 1.0"
    if off_user:
        user_agent = f"Nutrifitness - Mobile App - Version 1.0 - {off_user}"
    headers = {
        "User-Agent": user_agent,
    }
    auth = (off_user, off_pass) if off_user and off_pass else None
    try:
        res = requests.get(url, headers=headers, auth=auth, timeout=5)
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


def lookupBarcodeNutritonix(barcode):
    """Query Nutritionix API for a barcode. Returns simplified food dict or None."""
    app_id = os.environ.get("NUTRITIONIX_APP_ID", "")
    app_key = os.environ.get("NUTRITIONIX_APP_KEY", "")
    if not app_id or not app_key:
        return None
    url = "https://trackapi.nutritionix.com/v2/search/item"
    headers = {
        "x-app-id": app_id,
        "x-app-key": app_key,
        "Content-Type": "application/json",
    }
    try:
        res = requests.get(url, params={"upc": barcode}, headers=headers, timeout=5)
        if res.status_code != 200:
            return None
        data = res.json()
        foods = data.get("foods", [])
        if not foods:
            return None
        f = foods[0]
        nutrients = f.get("full_nutrients", [])
        # Map Nutritionix nutrient IDs to common names
        nutrient_map = {208: "calories_kcal", 203: "proteins_g", 204: "fat_g", 205: "carbohydrates_g"}
        parsed = {v: 0.0 for v in nutrient_map.values()}
        for n in nutrients:
            key = nutrient_map.get(n.get("attr_id"))
            if key:
                parsed[key] = n.get("value", 0.0)
        return {
            "name": f.get("food_name", "Unknown"),
            "brand": f.get("brand_name", ""),
            "barcode": barcode,
            "category": "",
            "allergens": [],
            "portion_size": f.get("serving_weight_grams", 100.0),
            "unit": "g",
            "nutrients": parsed,
            "micronutrients": {},
        }
    except Exception as e:
        print(f"Nutritionix lookup error: {e}")
        return None


BARCODE_CACHE_DAYS = 30


def lookupBarcode(barcode):
    """Multi-source barcode lookup with 30-day caching.

    Order: local DB cache → Nutritionix API → Open Food Facts API.
    Saves new results to the local DB automatically.
    Returns a (food_data_dict, cache_source) tuple, or (None, None) if not found.
    """
    from .models import FoodItem
    from django.utils import timezone as tz

    # 1. Check local DB (community shared + previously cached barcodes)
    food = FoodItem.objects.filter(barcode=barcode).first()
    if food and food.cached_at:
        age = tz.now() - food.cached_at
        if age.days < BARCODE_CACHE_DAYS:
            return simplifyFoodData_from_model(food), 'local'
        # Cache expired – fall through to re-fetch

    # 2. Try Nutritionix
    result = lookupBarcodeNutritonix(barcode)
    if result:
        _save_barcode_to_db(barcode, result, 'nutritionix')
        return result, 'nutritionix'

    # 3. Try Open Food Facts (with registered account credentials)
    result = readFoodData(barcode)
    if result:
        _save_barcode_to_db(barcode, result, 'off')
        return result, 'off'

    return None, None


def simplifyFoodData_from_model(food):
    """Convert a FoodItem model instance to the standard food data dict."""
    return {
        "name": food.name,
        "brand": "",
        "barcode": food.barcode,
        "category": food.category,
        "allergens": food.allergens or [],
        "portion_size": food.portion_size,
        "unit": food.unit,
        "nutrients": {
            "calories_kcal": food.calories,
            "proteins_g": food.protein,
            "fat_g": food.fat,
            "carbohydrates_g": food.carbs,
        },
        "micronutrients": food.micros or {},
    }


def _save_barcode_to_db(barcode, food_data, source):
    """Persist barcode lookup result to the local DB for community caching."""
    from .models import FoodItem
    from django.utils import timezone as tz

    nutrients = food_data.get("nutrients", {})
    micronutrients = food_data.get("micronutrients", {})
    FoodItem.objects.update_or_create(
        barcode=barcode,
        defaults={
            "name": food_data.get("name", "Unknown"),
            "category": food_data.get("category", ""),
            "allergens": food_data.get("allergens", []),
            "calories": nutrients.get("calories_kcal") or 0.0,
            "protein": nutrients.get("proteins_g") or 0.0,
            "fat": nutrients.get("fat_g") or 0.0,
            "carbs": nutrients.get("carbohydrates_g") or 0.0,
            "micros": micronutrients,
            "portion_size": food_data.get("portion_size", 100.0),
            "unit": food_data.get("unit", "g"),
            "cached_at": tz.now(),
            "cache_source": source,
        }
    )

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
                "portion_size": 100.0,
                "unit": "g",
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
        "portion_size": 100.0,
        "unit": "g",
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
#later feature
def generateFitnessPlan(x,y):
    return

GROCERY_TEMPLATES = {
    "gain": {
        "proteins": ["chicken breast", "ground beef (93% lean)", "eggs", "Greek yogurt", "cottage cheese", "canned tuna", "salmon"],
        "carbs": ["oats", "brown rice", "whole wheat bread", "sweet potatoes", "bananas", "pasta", "quinoa"],
        "fats": ["peanut butter", "almonds", "avocado", "olive oil", "walnuts"],
        "vegetables": ["spinach", "broccoli", "bell peppers", "carrots", "mixed greens"],
        "fruits": ["bananas", "apples", "blueberries", "oranges"],
        "dairy": ["whole milk", "cheddar cheese", "Greek yogurt"],
    },
    "lose": {
        "proteins": ["chicken breast", "turkey breast", "eggs", "Greek yogurt (non-fat)", "canned tuna", "shrimp", "tofu"],
        "carbs": ["oats", "brown rice", "sweet potatoes", "lentils", "chickpeas"],
        "fats": ["avocado", "almonds", "olive oil", "chia seeds"],
        "vegetables": ["spinach", "broccoli", "cauliflower", "zucchini", "cucumbers", "celery", "kale", "bell peppers"],
        "fruits": ["berries", "apples", "grapefruit", "watermelon"],
        "dairy": ["Greek yogurt (non-fat)", "skim milk", "cottage cheese (low-fat)"],
    },
    "maintain": {
        "proteins": ["chicken breast", "eggs", "Greek yogurt", "canned tuna", "salmon", "turkey"],
        "carbs": ["oats", "brown rice", "whole wheat bread", "potatoes", "quinoa"],
        "fats": ["avocado", "olive oil", "almonds", "peanut butter"],
        "vegetables": ["spinach", "broccoli", "mixed greens", "tomatoes", "bell peppers", "carrots"],
        "fruits": ["apples", "bananas", "berries", "oranges"],
        "dairy": ["Greek yogurt", "milk", "cheese"],
    },
}

DIET_EXCLUSIONS = {
    "vegan": ["chicken breast", "ground beef", "eggs", "Greek yogurt", "cottage cheese",
              "canned tuna", "salmon", "turkey", "shrimp", "whole milk", "cheddar cheese",
              "skim milk", "milk", "cheese", "turkey breast", "Greek yogurt (non-fat)",
              "cottage cheese (low-fat)", "Greek yogurt"],
    "vegetarian": ["chicken breast", "ground beef", "canned tuna", "salmon", "turkey",
                   "shrimp", "turkey breast"],
    "keto": ["oats", "brown rice", "whole wheat bread", "sweet potatoes", "bananas",
             "pasta", "quinoa", "lentils", "chickpeas", "potatoes"],
    "paleo": ["oats", "brown rice", "whole wheat bread", "pasta", "lentils", "chickpeas",
              "quinoa", "whole milk", "cheddar cheese", "skim milk", "milk", "cheese",
              "Greek yogurt", "Greek yogurt (non-fat)", "cottage cheese", "cottage cheese (low-fat)"],
    "gluten-free": ["whole wheat bread", "pasta", "oats"],
}

def generateGroceryList(goal, diet, allergies):
    """Generate a weekly grocery list based on goal, diet, and allergies (no external API)."""
    goal_key = goal.lower() if goal.lower() in GROCERY_TEMPLATES else "maintain"
    template = GROCERY_TEMPLATES[goal_key]

    exclusions = set()
    if diet:
        diet_lower = diet.lower()
        for diet_type, excluded in DIET_EXCLUSIONS.items():
            if diet_type in diet_lower:
                exclusions.update(excluded)

    if allergies:
        # FitnessProfile.allergies is stored as a dict (keys are allergen names) or list;
        # normalise to a flat list of lower-case strings.
        allergy_lower = [a.lower() for a in (allergies if isinstance(allergies, list) else list(allergies.keys()))]
        for allergen in allergy_lower:
            if "nut" in allergen or "peanut" in allergen:
                exclusions.update(["peanut butter", "almonds", "walnuts"])
            if "dairy" in allergen or "milk" in allergen or "lactose" in allergen:
                exclusions.update(["whole milk", "skim milk", "milk", "cheese", "cheddar cheese",
                                   "Greek yogurt", "Greek yogurt (non-fat)", "cottage cheese",
                                   "cottage cheese (low-fat)"])
            if "egg" in allergen:
                exclusions.add("eggs")
            if "gluten" in allergen or "wheat" in allergen:
                exclusions.update(["whole wheat bread", "pasta", "oats"])
            if "fish" in allergen or "seafood" in allergen:
                exclusions.update(["canned tuna", "salmon", "shrimp"])
            if "soy" in allergen:
                exclusions.add("tofu")

    grocery_list = {}
    for category, items in template.items():
        filtered = [item for item in items if item not in exclusions]
        if filtered:
            grocery_list[category] = filtered

    return grocery_list

def generateRecipe(ingredients, allergies, diet):
    if not ingredients:
        return None
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        return None
    client = Cerebras(api_key=api_key)

    ingredient_list = ', '.join(ingredients)
    allergy_text = ', '.join(allergies) if allergies else 'none'
    diet_text = ', '.join(diet) if diet else 'none'

    prompt = (
        f"You are a recipe generator. You MUST create a recipe using ONLY these exact ingredients: [{ingredient_list}].\n\n"
        f"You do not have to use all ingredients but you may not add your own"
        f"You do not need to use everything: ex user has fetichunni whitesauce,chicken,and rice. suggest alfreado dont suggest alfredo with a side of rice"
        f"STRICT RULES - violating any rule means failure:\n"
        f"1. Use ONLY ingredients from the list above. Do NOT add any ingredient not in this list.\n"
        f"2. Do NOT add proteins (chicken, beef, salmon, eggs, etc.) unless explicitly listed.\n"
        f"3. You MAY use commonly avalible oils and seasonings.\n"
        f"4. Every ingredient in your recipe must appear in the provided list.\n\n"
        f"Dietary preferences: {diet_text}.\n"
        f"Allergens to avoid: {allergy_text}.\n\n"
        f"Write a clear recipe with:\n"
        f"- Recipe name\n"
        f"- Ingredients (from the list ONLY, with quantities)\n"
        f"- Step-by-step instructions\n\n"
        f"At the very end, append ONLY this JSON on its own line (no markdown, no code block):\n"
        f'{{\"recipe_name\": \"NAME\", \"calories\": NUMBER, \"protein\": NUMBER, \"carbs\": NUMBER, \"fat\": NUMBER}}'
    )

    stream = client.chat.completions.create(
        model="llama3.1-8b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        stream=True,
        temperature=0.4,  # Lower temperature reduces hallucinations
        max_tokens=1000,
    )

    result_text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            result_text += delta

    return result_text




def extractNutrients(recipe_text):
    """Extract recipe name and nutrients from AI-generated recipe text."""
    import re
    import json

    result = {
        "recipe_name": "AI Generated Recipe",
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
    }

    # First try raw JSON at the end of the text (no code block)
    json_match = re.search(r'\{[^{}]*"recipe_name"[^{}]*\}\s*$', recipe_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            result["recipe_name"] = data.get("recipe_name", result["recipe_name"])
            result["calories"] = float(data.get("calories", 0) or 0)
            result["protein"] = float(data.get("protein", 0) or 0)
            result["carbs"] = float(data.get("carbs", 0) or 0)
            result["fat"] = float(data.get("fat", 0) or 0)
            return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: try to find a JSON code block in the text
    json_block = re.search(r'```json\s*(\{.*?\})\s*```', recipe_text, re.DOTALL | re.IGNORECASE)
    if json_block:
        try:
            data = json.loads(json_block.group(1))
            result["recipe_name"] = data.get("recipe_name", result["recipe_name"])
            result["calories"] = float(data.get("calories", 0) or 0)
            result["protein"] = float(data.get("protein", 0) or 0)
            result["carbs"] = float(data.get("carbs", 0) or 0)
            result["fat"] = float(data.get("fat", 0) or 0)
            return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: use regex to find common nutrient patterns
    cal_match = re.search(r'calories[:\s]+(\d+(?:\.\d+)?)\s*(?:kcal|cal)?', recipe_text, re.IGNORECASE)
    if cal_match:
        result["calories"] = float(cal_match.group(1))

    prot_match = re.search(r'protein[:\s]+(\d+(?:\.\d+)?)\s*g', recipe_text, re.IGNORECASE)
    if prot_match:
        result["protein"] = float(prot_match.group(1))

    carb_match = re.search(r'carb(?:ohydrate)?s?[:\s]+(\d+(?:\.\d+)?)\s*g', recipe_text, re.IGNORECASE)
    if carb_match:
        result["carbs"] = float(carb_match.group(1))

    fat_match = re.search(r'\bfat[:\s]+(\d+(?:\.\d+)?)\s*g', recipe_text, re.IGNORECASE)
    if fat_match:
        result["fat"] = float(fat_match.group(1))

    # Try to extract recipe name from the first markdown heading or bold title
    name_match = re.search(r'(?:^|\n)#\s+(.+)', recipe_text)
    if name_match:
        result["recipe_name"] = name_match.group(1).strip()
    else:
        bold_match = re.search(r'(?:^|\n)\*\*(.+?)\*\*', recipe_text)
        if bold_match:
            result["recipe_name"] = bold_match.group(1).strip()

    return result


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
