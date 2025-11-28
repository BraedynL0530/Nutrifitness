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
from .models import FitnessProfile, DailyLog, FoodItem, PantryItem

from . import utils
# Create your views here.


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
def dashboard(request):
    profile = FitnessProfile.objects.get(user=request.user)
    today = date.today()
    totals = DailyLog.get_daily_totals(profile, today)

    # Big stuff
    dailyCalories = totals.get("calories", 0)
    dailyProtein = totals.get("protein", 0)
    dailyCarbs = totals.get("carbs", 0)
    dailyFat = totals.get("fat", 0)

    data = {
        "nutrients": {
            "calories_kcal": dailyCalories,
            "fat_g": dailyFat,
            "carbohydrates_g": dailyCarbs,
            "proteins_g": dailyProtein,
        },
        "micronutrients": {
            "calcium_mg": totals.get("calcium_mg", 0),
            "iron_mg": totals.get("iron_mg", 0),
            "potassium_mg": totals.get("potassium_mg", 0),
            "magnesium_mg": totals.get("magnesium_mg", 0),
            "vitamin_c_mg": totals.get("vitamin_c_mg", 0),
            "vitamin_d_mg": totals.get("vitamin_d_mg", 0),
            "vitamin_a_mg": totals.get("vitamin_a_mg", 0),
            "zinc_mg": totals.get("zinc_mg", 0),
        },
        "goal_calories": profile.tdee,
        "eaten_calories": dailyCalories,
    }
#i think i fixed the mix match with barcode data? ill test tmrw its late lol
    return render(request, 'dashboard.html', {
        "data": data,
        "data_json": json.dumps(data)
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
    if request.method == 'POST':
        profile = FitnessProfile.objects.get(user=request.user)

        data = json.loads(request.body)
        barcode = data.get("barcode")
        name = data.get("name")
        grams = data.get("grams")
        qty = float(grams) / 100 if grams else 0
        nutrients = data.get("nutrients_100g") or {}
        micronutrients = json.loads(request.POST.get('micronutrients', "{}"))

        protein = (nutrients.get("proteins_g") or 0) * qty
        carbs = (nutrients.get("carbohydrates_g") or 0) * qty
        fat = (nutrients.get("fat_g") or 0) * qty
        calories = (nutrients.get("calories_kcal") or 0) * qty

        # micros:
        micros = {}
        for key, value in micronutrients.items():
            try:
                micros[key] = float(value) * qty
            except:
                micros[key] = 0

        food, created = FoodItem.objects.get_or_create(
            barcode=barcode,
            defaults={
                'name': name,
                'calories': calories,
                'protein': protein,
                'fat': fat,
                'carbs': carbs,
                'micros': micros
            }
        )
        DailyLog.objects.create(profile=profile, food=food, quantity=1)# I need to add meal types in the near future
        # in js and view

        return JsonResponse({"success": True, "food_id": barcode})

@csrf_exempt
def saveItem(request):
    if request.method == 'POST':
        profile = FitnessProfile.objects.get(user=request.user)

        data = json.loads(request.body)
        barcode = data.get("barcode")
        name = data.get("name")
        grams = data.get("grams")
        qty = float(grams) / 100 if grams else 0
        nutrients = data.get("nutrients_100g") or {}
        micronutrients = json.loads(request.POST.get('micronutrients', "{}"))

        protein = (nutrients.get("proteins_g") or 0) * qty
        carbs = (nutrients.get("carbohydrates_g") or 0) * qty
        fat = (nutrients.get("fat_g") or 0) * qty
        calories = (nutrients.get("calories_kcal") or 0) * qty

        # micros:
        micros = {}
        for key, value in micronutrients.items():
            try:
                micros[key] = float(value) * qty
            except:
                micros[key] = 0

        food, created = FoodItem.objects.get_or_create(
            barcode=barcode,
            defaults={
                'name': name,
                'calories': calories,
                'protein': protein,
                'fat': fat,
                'carbs': carbs,
                'micros': micros
            }
        )
        PantryItem.objects.create(profile=profile, food=food, quantity=1, unit="gram")

        return JsonResponse({"success": True, "food_id": barcode})



def myPantry(request):
    return render(request,"pantry.html")