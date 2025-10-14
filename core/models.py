from django.contrib.auth.models import User
from django.db import models

# Create your models here.
class FitnessProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sex = models.CharField(max_length=10, blank=True)
    birthYear = models.IntegerField(null=True, blank=True)
    heightCm = models.FloatField(null=True, blank=True)
    weightKg = models.FloatField(null=True, blank=True)
    goal = models.CharField(max_length=20, blank=True)
    lifestyle = models.CharField(max_length=20, blank=True)
    bmi = models.FloatField(null=True, blank=True)
    bmr = models.FloatField(null=True, blank=True)
    tdee = models.FloatField(null=True, blank=True)
    proteinIntake = models.FloatField(null=True, blank=True)
    diet = models.CharField(max_length=40, blank=True)
    allergies = models.JSONField(default=dict, blank=True)
    maxes = models.JSONField(default=dict, blank=True)  # {"bench":80, ...}