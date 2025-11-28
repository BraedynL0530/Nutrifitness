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
from .models import FitnessProfile, DailyLog, FoodItem

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

    # Micros
    micros_totals = {
        "Calcium": totals.get("calcium_mg", 0),
        "Iron": totals.get("iron_mg", 0),
        "Potassium": totals.get("potassium_mg", 0),
        "Magnesium": totals.get("magnesium_mg", 0),
        "Vitamin C": totals.get("vitamin_c_mg", 0),
        "Vitamin D": totals.get("vitamin_d_mg", 0),
        "Vitamin A": totals.get("vitamin_a_mg", 0),
        "Zinc": totals.get("zinc_mg", 0),
    }
    # Real data now that upload is being implemented
    data = {
        "macros": {
            "Protein": dailyProtein,
            "Carbs": dailyCarbs,
            "Fat": dailyFat
        },
        "micros": micros_totals,
        "goal_calories": profile.tdee,
        "eaten_calories": dailyCalories,
    }


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

        calories = (nutrients.get('calories_kcal') or 0) * qty
        protein = (nutrients.get('protein_g') or 0) * qty
        fat = (nutrients.get('fat_g') or 0) * qty
        carbs = (nutrients.get('carbs_g') or 0) * qty

        # micros: multiply each micro by qty
        micros = {k: v * qty for k, v in (nutrients.get('micros') or {}).items()}

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




def myPantry(request):
    return render(request,"pantry.html")