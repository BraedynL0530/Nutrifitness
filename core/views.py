import json
from datetime import date
import cv2
import numpy as np
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from django.utils import timezone
from .models import FitnessProfile, DailyLog, PantryItem,FoodItem,WeeklySummary, WeightLog
from . import utils
import uuid
from django.core.cache import cache
def register(request):
    #planning to add oauth later
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # auto-login
            return redirect("questionnaire")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})

@login_required(login_url='/login/')
def questionnaire(request):
    try:
        profile = FitnessProfile.objects.get(user=request.user)
        return redirect("dashboard")
    except FitnessProfile.DoesNotExist:
        return render(request, 'questionnaire.html')

@csrf_exempt
def questionnaireData(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        if FitnessProfile.objects.filter(user=request.user).exists():
            return JsonResponse({'status': 'already exists'})

        try:
            height = float(data.get('height') or 0)
            weight = float(data.get('weight') or 0)
            age = int(data.get('age') or 18)
            lifestyle = data.get('lifestyle') or 'Sedentary'
        except (ValueError, TypeError):
            return JsonResponse({'status': 'invalid data'}, status=400)

        if not height or not weight:
            return JsonResponse({'status': 'missing fields'}, status=400)

        if lifestyle not in utils.lifeStyleFactors:
            lifestyle = 'Sedentary'

        bmr = utils.calcBmr(weight, height, age, data.get('sex', 'male'))

        profile = FitnessProfile.objects.create(
            user=request.user,
            heightCm=height,
            weightKg=weight,
            sex=data.get('sex', 'male'),
            goal=data.get('goal', 'maintain'),
            lifestyle=lifestyle,
            diet=data.get('diet', ''),
            allergies=data.get('allergies', []),
            bmi=utils.calcBmi(weight, height),
            bmr=bmr,
            tdee=utils.calcTdee(bmr, utils.lifeStyleFactors[lifestyle]),
            proteinIntake=utils.proteinTarget(weight, data.get('goal', 'maintain')),
            maxes={
                'bench': data.get('bench') or None,
                'squat': data.get('squat') or None,
                'deadlift': data.get('deadlift') or None,
            }
        )
        WeightLog.objects.create(profile=profile, weight=weight)
        return JsonResponse({'status': 'success'})

@login_required(login_url='/login/')
def dashboard(request):
    try:
        profile = FitnessProfile.objects.select_related('user').get(user=request.user)
    except FitnessProfile.DoesNotExist:
        return redirect("questionnaire")

    today = timezone.localdate()
    last_week_start = today - timedelta(days=today.weekday() + 7)  # Last Monday
    WeeklySummary.create_from_daily_logs(profile, last_week_start)

    weight_logs = profile.weight_logs.all()[:30]

    # Get ML prediction
    predicted_change = utils.getWeightPrediction(profile) # No beuno (yet) other than that project done!

    totals = DailyLog.get_daily_totals(profile, today)
    dailyCalories = totals.get("calories")
    dailyProtien = totals.get("protein") # Misspelled protein found the issue
    dailyCarbs = totals.get("carbs")
    dailyFat = totals.get("fat")
    # Now real DB data,
    data = {
        "macros": {
            "Protein": dailyProtien,
            "Carbs": dailyCarbs,
            "Fat": dailyFat
        },
        "micros": {
            "calcium_mg": totals.get("calcium_mg", 0),
            "iron_mg": totals.get("iron_mg", 0),
            "potassium_mg": totals.get("potassium_mg", 0),
            "magnesium_mg": totals.get("magnesium_mg", 0),
            "vitamin-C_mg": totals.get("vitamin-C_mg", 0),
            "vitamin-D_mg": totals.get("vitamin-D_mg", 0),
        },
        "goal_calories": profile.tdee,
        "eaten_calories": dailyCalories,
    }

    weightData = {
        'current_weight': profile.get_latest_weight(),
        'prediction': predicted_change,
        'history': [
            {'date': log.date.strftime('%Y-%m-%d'), 'weight': log.weight}
            for log in weight_logs
        ]
    }

    foods = DailyLog.get_daily_foods(profile, today)

    foodsData = foods

    print(predicted_change)
    print(weightData)
    print("DEBUG current_weight:", weightData.get('current_weight'))
    print("DEBUG history:", weightData.get('history'))
    return render(request, 'dashboard.html', {
        "data": data,
        "foodsData": foodsData,
        "weightData": weightData,       # Removed redundant json data template does it for me
        "user":request.user,
    })


@login_required(login_url='/login/')
def myPantry(request):
    profile = FitnessProfile.objects.get(user=request.user)
    pantry_items = profile.pantry.prefetch_related('food').all()

    # Convert QuerySet to list of dicts
    pantry_data = []
    for item in pantry_items:
        pantry_data.append({
            'name': item.food.name,
            'brand': item.food.category,
            'category': item.food.category,
            'calories': item.food.calories, # Fixxed had quantity n stuff bc i reused the dashboard/daily item
        })

    return render(request, 'pantry.html', {
        'pantry_data': json.dumps(pantry_data)
    })

@csrf_exempt
def uploadBarcode(request):
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({'error':'No image uploaded!'}, status=400)
    npImg = np.frombuffer(image.read(), np.uint8)
    frame = cv2.imdecode(npImg, cv2.IMREAD_COLOR)
    results = utils.barcodeScanner(frame)

    if not results:
        return JsonResponse({"error": "No barcode found"}, status=400)

    barcode = results

    return JsonResponse({"barcode": barcode})

def searchFood(request):
    profile = FitnessProfile.objects.get(user=request.user)

    if not check_rate_limit(request.user.id, "search", profile.isPremium):
        return JsonResponse({"error": "Search limit reached for today."}, status=429)

    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"error": "Query too short"}, status=400)
    results = utils.searchUSDA(query)
    return JsonResponse({"results": results})

@csrf_exempt
def generateBarcode(name):
    barcode = str(uuid.uuid4())
    return f"manual_{uuid.uuid4().hex[:12]}"


@csrf_exempt
def saveFood(request):
    if request.method == "POST":
        data = json.loads(request.body)
        barcode = data.get("barcode", "")
        name = data.get("name", "")
        grams = data.get("grams", 0)
        nutrients = data.get("nutrients", {})
        micronutrients = data.get("micronutrients", {})
        category = data.get("category", "")
        allergens = data.get("allergens", [])

        if not barcode  or barcode == "unknown":
            barcode = generateBarcode(name)
        if grams <= 0:
            return JsonResponse({"error": "Invalid grams"}, status=400)

        food, created = FoodItem.objects.get_or_create(
            barcode=barcode,
            defaults={
                "name": name,
                "category": category,
                "allergens": allergens,
                "calories": nutrients.get("calories_kcal", 0.0),
                "protein": nutrients.get("proteins_g", 0.0),
                "fat": nutrients.get("fat_g", 0.0),
                "carbs": nutrients.get("carbohydrates_g", 0.0),
                "micros":micronutrients
            })

        profile = FitnessProfile.objects.select_related('user').get(user=request.user)
        DailyLog.objects.create(food=food, quantity=float(grams / 100), profile=profile)

        print(f"✅ Saved: {name} - {grams}g (quantity={grams / 100})")
        return JsonResponse({
            "success": True,
            "food_name": name,
            "grams": grams
        })

@csrf_exempt
def saveItem(request):
    if request.method == "POST":
        data = json.loads(request.body)
        barcode = data.get("barcode", "")
        name = data.get("name", "")
        nutrients = data.get("nutrients", {})
        micronutrients = data.get("micronutrients", {})
        category = data.get("category", "")
        allergens = data.get("allergens", [])

        food, created = FoodItem.objects.get_or_create(
            barcode=barcode,
            defaults={
                "name": name,
                "category": category,
                "allergens": allergens,
                "calories": nutrients.get("calories_kcal", 0.0),
                "protein": nutrients.get("proteins_g", 0.0),
                "fat": nutrients.get("fat_g", 0.0),
                "carbs": nutrients.get("carbohydrates_g", 0.0),
                "micros": micronutrients
            })

        PantryItem.objects.create(food=food, profile=request.user.fitnessprofile)
        print(f"✅ Saved: {name}")
        return JsonResponse({
            "success": True,
            "food_name": name,
        })

@csrf_exempt
def saveWeight(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        weight = data.get('weight')
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid weight'}, status=400)

        if weight <= 0 or weight > 500:
            return JsonResponse({'error': 'Invalid weight'}, status=400)

        profile = FitnessProfile.objects.get(user=request.user)
        profile.update_weight(weight)
        return JsonResponse({'status': 'success'})
    return None


def check_rate_limit(user_id, action, is_premium):
    #True = allowed
    limits = {
        "recipe": {"free": 2, "premium": 20},
        "search": {"free": 30, "premium": 200},
    }

    tier = "premium" if is_premium else "free"
    limit = limits[action][tier]

    key = f"rl_{action}_{user_id}"
    current = cache.get(key, 0)

    if current >= limit:
        return False

    cache.set(key, current + 1, timeout=86400)  # resets every day
    return True


@csrf_exempt
def aiRecipe(request):
    try:
        profile = FitnessProfile.objects.get(user=request.user)

        if not check_rate_limit(request.user.id, "recipe", profile.isPremium):
            limit = 20 if profile.isPremium else 2
            return JsonResponse({
                "error": f"Daily limit of {limit} recipes reached.",
                "upgrade_needed": not profile.isPremium
            }, status=429)

        # Get ingredients from pantry
        ingredients = list(profile.pantry.select_related('food').values_list('food__name', flat=True))

        # Check if pantry is empty
        if not ingredients:
            return JsonResponse({
                "error": "Your pantry is empty! Add some items first."
            }, status=400)

        # Get allergies
        allergies = profile.allergies if profile.allergies else {}
        allergy_list = list(allergies.keys()) if isinstance(allergies, dict) else []

        # Get diet
        diet_list = [profile.diet] if profile.diet else []

        print(f"Generating recipe with:")
        print(f"  Ingredients: {ingredients}")
        print(f"  Allergies: {allergy_list}")
        print(f"  Diet: {diet_list}")

        recipe = utils.generateRecipe(ingredients, allergy_list, diet_list)

        if not recipe:
            return JsonResponse({
                "error": "Failed to generate recipe. Try again."
            }, status=500)

        nutrients = utils.extractNutrients(recipe)
        return JsonResponse({"recipe": recipe, "nutrients": nutrients})

    except FitnessProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found"}, status=404)
    except Exception as e:
        print(f"❌ Recipe generation error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

