import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt

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
        heightCm = data.get('height')
        weightKg = data.get('weight')
        sex = data.get('sex')
        lifeStyle = data.get('activity_level')
        maxes = {
            'bench': data.getdata.get('bench'),
            'squat': data.get('squat'),
            'deadlift': data.get('deadlift')
        }
        bmi = utils.calcBmi(weightKg, heightCm)
        bmr = utils.calcBmr(weightKg,heightCm,sex)
        tdee = utils.calcTdee(bmr, utils.lifeStyleFactors[lifeStyle])

        #note to self we need to add age to register or questionnaire, and goals near the end.
        #dont forget to save to Profile table as well
        print(data)
        return JsonResponse({'status': 'success'})
