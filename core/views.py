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
from .models import FitnessProfile, DailyLog

from . import utils
# Create your views here.
def home(request):
    return render(request, 'home.html')

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
    dailyCalories = totals.get("calories")
    dailyProtien = totals.get("protien")
    dailyCarbs = totals.get("carbs")
    dailyFat = totals.get("fat")
    # Mock/test data — realistic sample day
    data = {
        "macros": {
            "Protein": 122,
            "Carbs": 250,
            "Fat": 70
        },
        "micros": {
            "Iron": 18,
            "Vitamin C": 85,
            "Calcium": 900,
            "Magnesium": 250,
            "Vitamin D": 15,
            "Potassium": 2800
        },
        "goal_calories": 2600,
        "eaten_calories": 1820,
    }


    return render(request, 'dashboard.html', {
        "data": data,
        "data_json": json.dumps(data)
    })
    # old/real DB data{
      #  "totals": totals,
      #  "total_calories":dailyCalories,
      #  "total_protein":dailyProtien,
      #  "total_carbs":dailyCarbs,
      #  "total_fat": dailyFat,
      #  "goalCalories": profile.tdee,
      #  "goalProtein": profile.proteinIntake
    #})

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

def myPantry(request):
    return render(request,"pantry.html")