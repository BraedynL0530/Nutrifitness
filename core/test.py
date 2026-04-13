from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import FitnessProfile, WeightLog, DailyLog, FoodItem
from django.utils import timezone

class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@test.com'
        )

    def test_register(self):
        res = self.client.post('/register/', {
            'username': 'newuser',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        })
        self.assertEqual(User.objects.filter(username='newuser').count(), 1)

    def test_dashboard_accessible_without_login(self):
        res = self.client.get('')
        self.assertEqual(res.status_code, 200)

    def test_dashboard_no_profile_redirects(self):
        self.client.login(username='testuser', password='testpass123')
        res = self.client.get('')
        self.assertRedirects(res, '/More-About-You')


class QuestionnaireTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_submit_valid(self):
        res = self.client.post('/questionnaire-post',
            data='{"height":"175","weight":"70","sex":"male","age":"20","lifestyle":"Sedentary","goal":"maintain","diet":"None","allergies":[]}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(FitnessProfile.objects.filter(user=self.user).exists())

    def test_submit_twice(self):
        # Should not crash on duplicate
        data = '{"height":"175","weight":"70","sex":"male","age":"20","lifestyle":"Sedentary","goal":"maintain","diet":"None","allergies":[]}'
        self.client.post('/questionnaire-post', data=data, content_type='application/json')
        res = self.client.post('/questionnaire-post', data=data, content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(FitnessProfile.objects.filter(user=self.user).count(), 1)

    def test_missing_fields(self):
        res = self.client.post('/questionnaire-post',
            data='{"height":"","weight":"","sex":"male","age":"20","lifestyle":"Sedentary","goal":"maintain","diet":"None","allergies":[]}',
            content_type='application/json'
        )
        # Should not 500
        self.assertNotEqual(res.status_code, 500)


class FoodLoggingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.profile = FitnessProfile.objects.create(
            user=self.user,
            heightCm=175, weightKg=70,
            sex='male', tdee=2000
        )
        WeightLog.objects.create(profile=self.profile, weight=70)

    def test_log_valid_food(self):
        res = self.client.post('/api/food-log/',
            data='{"barcode":"123456","name":"Chicken","grams":100,"nutrients":{"calories_kcal":165,"proteins_g":31,"fat_g":3.6,"carbohydrates_g":0},"micronutrients":{}}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(DailyLog.objects.count(), 1)

    def test_log_zero_grams(self):
        res = self.client.post('/api/food-log/',
            data='{"barcode":"123456","name":"Chicken","grams":0,"nutrients":{},"micronutrients":{}}',
            content_type='application/json'
        )
        # Should not create a log entry
        self.assertEqual(DailyLog.objects.count(), 0)

    def test_log_manual_no_barcode(self):
        # Manual entry with no barcode should use uuid fallback
        res = self.client.post('/api/food-log/',
            data='{"barcode":"","name":"Homemade soup","grams":200,"nutrients":{"calories_kcal":100,"proteins_g":5,"fat_g":2,"carbohydrates_g":10},"micronutrients":{}}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)

    def test_log_same_barcode_twice(self):
        # get_or_create should handle this
        data = '{"barcode":"SAME123","name":"Test food","grams":100,"nutrients":{"calories_kcal":100,"proteins_g":5,"fat_g":2,"carbohydrates_g":10},"micronutrients":{}}'
        self.client.post('/api/food-log/', data=data, content_type='application/json')
        res = self.client.post('/api/food-log/', data=data, content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(FoodItem.objects.filter(barcode='SAME123').count(), 1)


class WeightTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=70,
            sex='male', tdee=2000
        )

    def test_log_valid_weight(self):
        res = self.client.post('/api/weight-log/',
            data='{"weight": 71.5}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(WeightLog.objects.count(), 1)

    def test_log_negative_weight(self):
        res = self.client.post('/api/weight-log/',
            data='{"weight": -10}',
            content_type='application/json'
        )
        self.assertEqual(WeightLog.objects.count(), 0)

    def test_log_insane_weight(self):
        res = self.client.post('/api/weight-log/',
            data='{"weight": 9999}',
            content_type='application/json'
        )
        self.assertEqual(WeightLog.objects.count(), 0)


class DashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=70,
            sex='male', tdee=2000, bmr=1700
        )
        WeightLog.objects.create(profile=self.profile, weight=70)

    def test_dashboard_loads(self):
        res = self.client.get('')
        self.assertEqual(res.status_code, 200)

    def test_dashboard_zero_food(self):
        # New user with no food logged should not crash
        res = self.client.get('')
        self.assertEqual(res.status_code, 200)

    def test_dashboard_passes_streak_context(self):
        res = self.client.get('')
        self.assertIn('streakInfo', res.context)
        self.assertIn('heatmapData', res.context)
        self.assertIn('is_premium', res.context)


class StreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='streakuser', password='testpass123'
        )
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=70,
            sex='male', tdee=2000
        )

    def test_first_log_starts_streak(self):
        self.profile.update_streak()
        self.assertEqual(self.profile.streak_count, 1)
        self.assertEqual(self.profile.streak_last_logged, timezone.now().date())

    def test_same_day_log_no_increment(self):
        self.profile.update_streak()
        self.profile.update_streak()
        self.assertEqual(self.profile.streak_count, 1)

    def test_streak_breaks_when_missed(self):
        from datetime import timedelta
        # Simulate having logged 2 days ago
        self.profile.streak_count = 5
        self.profile.streak_last_logged = timezone.now().date() - timedelta(days=2)
        self.profile.save()
        self.profile.update_streak()
        # Should reset to 1 (new streak starting today)
        self.assertEqual(self.profile.streak_count, 1)
        # Should have saved the pre-break count
        self.assertEqual(self.profile.streak_at_break, 5)

    def test_effective_streak_zero_when_broken(self):
        from datetime import timedelta
        # Simulate having logged 3 days ago
        self.profile.streak_count = 10
        self.profile.streak_last_logged = timezone.now().date() - timedelta(days=3)
        self.profile.save()
        self.profile.refresh_streak_state()
        # Effective streak should be 0 (broken)
        self.assertEqual(self.profile.get_effective_streak(), 0)

    def test_can_restore_premium_yesterday(self):
        from datetime import timedelta
        today = timezone.now().date()
        # Simulate streak broke yesterday
        self.profile.isPremium = True
        self.profile.streak_count = 1
        self.profile.streak_last_logged = today
        self.profile.streak_broken_date = today - timedelta(days=1)
        self.profile.streak_at_break = 7
        self.profile.save()
        self.assertTrue(self.profile.can_restore_streak())

    def test_cannot_restore_non_premium(self):
        from datetime import timedelta
        today = timezone.now().date()
        self.profile.isPremium = False
        self.profile.streak_broken_date = today - timedelta(days=1)
        self.profile.streak_at_break = 7
        self.profile.save()
        self.assertFalse(self.profile.can_restore_streak())

    def test_cannot_restore_two_days_ago(self):
        from datetime import timedelta
        today = timezone.now().date()
        self.profile.isPremium = True
        self.profile.streak_broken_date = today - timedelta(days=2)
        self.profile.streak_at_break = 7
        self.profile.save()
        self.assertFalse(self.profile.can_restore_streak())

    def test_restore_sets_streak(self):
        from datetime import timedelta
        today = timezone.now().date()
        self.profile.isPremium = True
        self.profile.streak_count = 1  # logged today
        self.profile.streak_last_logged = today
        self.profile.streak_broken_date = today - timedelta(days=1)
        self.profile.streak_at_break = 7
        self.profile.save()
        success = self.profile.restore_streak()
        self.assertTrue(success)
        self.assertEqual(self.profile.streak_count, 8)  # at_break(7) + 1 for today
        self.assertIsNone(self.profile.streak_broken_date)
        self.assertEqual(self.profile.restore_last_used, today)

    def test_restore_weekly_limit(self):
        from datetime import timedelta
        today = timezone.now().date()
        self.profile.isPremium = True
        self.profile.streak_count = 1
        self.profile.streak_last_logged = today
        self.profile.streak_broken_date = today - timedelta(days=1)
        self.profile.streak_at_break = 5
        self.profile.restore_last_used = today - timedelta(days=3)  # used 3 days ago
        self.profile.save()
        # Should not be able to restore (< 7 days since last use)
        self.assertFalse(self.profile.can_restore_streak())


class WeightUnitTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='weightuser', password='testpass123'
        )
        self.client.login(username='weightuser', password='testpass123')
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=70,
            sex='male', tdee=2000
        )

    def test_log_weight_in_kg(self):
        res = self.client.post('/api/weight-log/',
            data='{"weight": 75.0, "unit": "kg"}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.profile.refresh_from_db()
        self.assertAlmostEqual(self.profile.weightKg, 75.0, places=1)
        self.assertEqual(self.profile.weight_unit_preference, 'kg')

    def test_log_weight_in_lbs(self):
        res = self.client.post('/api/weight-log/',
            data='{"weight": 165.0, "unit": "lbs"}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.profile.refresh_from_db()
        # 165 lbs * 0.453592 = 74.84 kg
        self.assertAlmostEqual(self.profile.weightKg, 74.84, places=1)
        self.assertEqual(self.profile.weight_unit_preference, 'lbs')