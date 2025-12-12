from collections import defaultdict
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Sum


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

    def get_latest_weight(self):
        """Get most recent logged weight, or profile weight as fallback"""
        latest_log = self.weight_logs.first()  # ordered by date
        return latest_log.weight if latest_log else self.weightKg

    def update_weight(self, new_weight):
        """Update current weight and create log entry"""
        self.weightKg = new_weight
        self.save()
        WeightLog.objects.create(profile=self, weight=new_weight)


class WeightLog(models.Model):
    profile = models.ForeignKey(FitnessProfile, on_delete=models.CASCADE, related_name="weight_logs")
    weight = models.FloatField()
    date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-date','-id'] # Prevents same day logging being weird

    def __str__(self):
        return f"{self.profile.user.username} - {self.weight}kg on {self.date}"

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
                    if value is not None:
                        totals[key] += value * log.quantity

        return dict(totals)

    @classmethod
    def get_daily_foods(cls, profile, date=None):
        """Return food items consumed on a given day."""
        if date is None:
            date = timezone.localdate()

        logs = cls.objects.filter(profile=profile, date=date)
        foods = []

        for log in logs:
            foods.append({
                'name': log.food.name,
                'calories': (log.food.calories or 0) * log.quantity,
                'quantity': log.quantity,
            })

        return foods


class WeeklySummary(models.Model):
    profile = models.ForeignKey(FitnessProfile, on_delete=models.CASCADE, related_name="weekly_summary")
    week_start = models.DateField()
    week_end = models.DateField()

    # Nutrients
    avg_daily_calories = models.FloatField(default=0)
    avg_daily_protein = models.FloatField(default=0)
    avg_daily_carbs = models.FloatField(default=0)
    avg_daily_fat = models.FloatField(default=0)

    # Deficit(or surplus lol)
    deficit = models.FloatField(default=0)

    # Weight tracking
    starting_weight = models.FloatField(default=0)
    ending_weight = models.FloatField(default=0)
    weight_change = models.FloatField(default=0)

    class meta:
        ordering = ['-week_start']
        unique_together = ('profile', 'week_start')

    def __str__(self):
        return f"{self.profile.user.username} - Week of {self.week_start}"

    @classmethod
    def create_from_daily_logs(cls, profile, week_start):
        # Make weekly summary from DailyLog

        week_end = week_start + timedelta(days=6)

        # Get all daily logs for week
        logs = DailyLog.objects.filter(
            profile=profile,
            date__range=[week_start, week_end]
        )

        if not logs.exists():
            return None

        # Calc daily averages (if you're new to the chat calc is short for calculate)
        total_days = 7
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0

        # Group by day and sum
        from collections import defaultdict
        daily_totals = defaultdict(lambda: {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0})

        for log in logs:
            day = log.date
            daily_totals[day]['calories'] += (log.food.calories or 0) * log.quantity
            daily_totals[day]['protein'] += (log.food.protein or 0) * log.quantity
            daily_totals[day]['carbs'] += (log.food.carbs or 0) * log.quantity
            daily_totals[day]['fat'] += (log.food.fat or 0) * log.quantity

        # Calculate averages
        num_days = len(daily_totals)
        if num_days == 0:
            return None

        avg_calories = sum(d['calories'] for d in daily_totals.values()) / num_days
        avg_protein = sum(d['protein'] for d in daily_totals.values()) / num_days
        avg_carbs = sum(d['carbs'] for d in daily_totals.values()) / num_days
        avg_fat = sum(d['fat'] for d in daily_totals.values()) / num_days

        # Get weights
        start_weight_log = WeightLog.objects.filter(
            profile=profile,
            date__lte=week_start
        ).first()

        end_weight_log = WeightLog.objects.filter(
            profile=profile,
            date__lte=week_end
        ).first()

        starting_weight = start_weight_log.weight if start_weight_log else profile.weightKg
        ending_weight = end_weight_log.weight if end_weight_log else starting_weight
        weight_change = ending_weight - starting_weight if starting_weight and ending_weight else 0

        # Create summary
        summary, created = cls.objects.update_or_create(
            profile=profile,
            week_start=week_start,
            defaults={
                'week_end': week_end,
                'avg_daily_calories': round(avg_calories, 2),
                'avg_daily_protein': round(avg_protein, 2),
                'avg_daily_carbs': round(avg_carbs, 2),
                'avg_daily_fat': round(avg_fat, 2),
                'deficit': round(profile.tdee - avg_calories, 2),
                'starting_weight': round(starting_weight, 2) if starting_weight else None,
                'ending_weight': round(ending_weight, 2) if ending_weight else None,
                'weight_change': round(weight_change, 2),
            }
        )

        return summary

