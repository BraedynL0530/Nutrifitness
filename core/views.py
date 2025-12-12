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
from .models import FitnessProfile, DailyLog, PantryItem,FoodItem,WeeklySummary
from . import utils

def register(request):
    #planning to add oauth later
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # auto-login
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})

@login_required(login_url='/login/')
def questionnaire(request):
    return render(request, 'questionnaire.html')

@csrf_exempt
def questionnaireData(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        profile = FitnessProfile.objects.create(
            user=request.user,
            heightCm=float(data.get('height')),
            weightKg=float(data.get('weight')),
            sex=data.get('sex'),
            lifestyle=data.get('activity_level'),
            bmi=utils.calcBmi(float(data.get('weight')), float(data.get('height'))),
            bmr=utils.calcBmr(
                float(data.get('weight')),
                float(data.get('height')),
                data.get('age', 18),  # default untill i add that to login DONT FORGET TO ADD EMAIL AND OAUTH TO LOGIN!
                data.get('sex')
            ),
            tdee=utils.calcTdee(
                utils.calcBmr(
                    float(data.get('weight')),
                    float(data.get('height')),
                    data.get('age', 18),
                    data.get('sex')
                ),
                utils.lifeStyleFactors[data.get('activity_level')]
            ),
            proteinIntake=utils.proteinTarget(float(data.get('weight')), data.get('goal')),
            maxes={
                'bench': data.get('bench') or None,
                'squat': data.get('squat') or None,
                'deadlift': data.get('deadlift') or None,
            }
        )
        #



        print(data)
        return JsonResponse({'status': 'success'})

@login_required(login_url='/login/')
def dashboard(request):
    profile = FitnessProfile.objects.get(user=request.user)

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
        "weightData": weightData,       #removed redundant json data
        "user":request.user,
    })


@login_required(login_url='/login/')
def myPantry(request):
    profile = FitnessProfile.objects.get(user=request.user)
    pantry_items = profile.pantry.select_related('food').all()

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

        DailyLog.objects.create(food=food, quantity=float(grams/100), profile=request.user.fitnessprofile)

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
        profile = FitnessProfile.objects.get(user=request.user)
        data = json.loads(request.body)
        weight = data.get('weight')
        profile.update_weight(weight)
        return JsonResponse({'status': 'success'})
    return None


@csrf_exempt
def aiRecipe(request):
    try:
        profile = FitnessProfile.objects.get(user=request.user)

        # Get ingredients from pantry
        ingredients = list(profile.pantry.all().values_list('food__name', flat=True))

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

        return JsonResponse({"recipe": recipe})

    except FitnessProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found"}, status=404)
    except Exception as e:
        print(f"❌ Recipe generation error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

