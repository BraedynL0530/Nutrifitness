from collections import defaultdict

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


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

    def __str__(self):
        return self.user.username


class FoodItem(models.Model):
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=50, unique=True, null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    calories = models.FloatField(null=True, blank=True)
    protein = models.FloatField(null=True, blank=True)
    fat = models.FloatField(null=True, blank=True)
    carbs = models.FloatField(null=True, blank=True)
    micros = models.JSONField(default=dict, blank=True)  # vitamins, minerals, etc.
    allergens = models.JSONField(default=list, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PantryItem(models.Model):
    # linked to FitnessProfile instead of raw User
    profile = models.ForeignKey(FitnessProfile, on_delete=models.CASCADE, related_name="pantry")
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'food')  # one of each food per user

    def __str__(self):
        return f"{self.food.name} ({self.profile.user.username})"

class DailyLog(models.Model):
    profile = models.ForeignKey(FitnessProfile, on_delete=models.CASCADE, related_name="daily_logs")
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.FloatField(default=1.0)
    date = models.DateField(auto_now_add=True)
    meal_type = models.CharField(
        max_length=20,
        choices=[
            ('breakfast', 'Breakfast'),
            ('lunch', 'Lunch'),
            ('dinner', 'Dinner'),
            ('snack', 'Snack'),
        ],
        default='lunch'
    )

    def __str__(self):
        return f"{self.food.name} ({self.meal_type}) - {self.profile.user.username}"

    @classmethod
    def get_daily_totals(cls, profile, date=None):
        """Return total calories, macros, and micros for a profile on a given day."""
        if date is None:
            date = timezone.localdate()

        logs = cls.objects.filter(profile=profile, date=date)
        totals = defaultdict(float)

        for log in logs:
            totals['calories'] += (log.food.calories or 0) * log.quantity
            totals['protein'] += (log.food.protein or 0) * log.quantity
            totals['carbs'] += (log.food.carbs or 0) * log.quantity
            totals['fat'] += (log.food.fat or 0) * log.quantity

            if log.food.micros:
                for key, value in log.food.micros.items():
                    totals[key] += value * log.quantity

        return dict(totals)