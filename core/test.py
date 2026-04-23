from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import FitnessProfile, WeightLog, DailyLog, FoodItem, ExerciseLog
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


class DailyFoodsTimezoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tzuser', password='testpass123'
        )
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=70,
            sex='male', tdee=2000
        )
        self.food = FoodItem.objects.create(
            name='Test Food',
            calories=100.0,
            protein=5.0,
            fat=2.0,
            carbs=10.0,
        )

    def test_get_daily_foods_uses_local_date_multiple_timezones(self):
        """Test that get_daily_foods returns today's foods in the user's local timezone, not yesterday's."""
        import pytz
        from datetime import timedelta

        timezones = [
            'US/Eastern',
            'US/Pacific',
            'Asia/Tokyo',
            'Australia/Sydney',
        ]

        for tz_name in timezones:
            with timezone.override(pytz.timezone(tz_name)):
                DailyLog.objects.filter(profile=self.profile).delete()

                today = timezone.localdate()
                yesterday = today - timedelta(days=1)

                # Create food log for TODAY
                log_today = DailyLog.objects.create(
                    profile=self.profile,
                    food=self.food,
                    quantity=1.0,
                    date=today
                )

                # Create food log for YESTERDAY (should not appear)
                log_yesterday = DailyLog.objects.create(
                    profile=self.profile,
                    food=self.food,
                    quantity=1.0,
                    date=yesterday
                )

                # Get daily foods for TODAY
                foods = DailyLog.get_daily_foods(self.profile, today)

                self.assertEqual(len(foods), 1, f"Failed for {tz_name}: expected 1 food, got {len(foods)}")
                self.assertEqual(foods[0]['name'], self.food.name, f"Failed for {tz_name}: wrong food name")
                self.assertIn('id', foods[0], f"Failed for {tz_name}: missing id field")

                # Get daily foods for YESTERDAY
                foods_yesterday = DailyLog.get_daily_foods(self.profile, yesterday)
                self.assertEqual(len(foods_yesterday), 1, f"Failed for {tz_name}: expected 1 yesterday food, got {len(foods_yesterday)}")
                self.assertNotEqual(
                    foods[0]['id'], foods_yesterday[0]['id'],
                    f"Failed for {tz_name}: today and yesterday IDs should differ"
                )

class BulkDeleteFoodLogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='bulkuser', password='testpass123')
        self.client.login(username='bulkuser', password='testpass123')
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=70, sex='male', tdee=2000
        )
        self.food = FoodItem.objects.create(name='Test Food', calories=100.0)
        self.log1 = DailyLog.objects.create(profile=self.profile, food=self.food, quantity=1.0)
        self.log2 = DailyLog.objects.create(profile=self.profile, food=self.food, quantity=1.0)

    def test_bulk_delete_selected(self):
        res = self.client.post(
            '/api/food-log/bulk-delete/',
            data='{"ids": [' + str(self.log1.id) + ',' + str(self.log2.id) + ']}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(DailyLog.objects.count(), 0)

    def test_bulk_delete_empty_ids(self):
        res = self.client.post(
            '/api/food-log/bulk-delete/',
            data='{"ids": []}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(DailyLog.objects.count(), 2)

    def test_bulk_delete_only_own_logs(self):
        other_user = User.objects.create_user(username='otheruser2', password='testpass123')
        other_profile = FitnessProfile.objects.create(
            user=other_user, heightCm=170, weightKg=65, sex='female', tdee=1800
        )
        other_log = DailyLog.objects.create(profile=other_profile, food=self.food, quantity=1.0)
        res = self.client.post(
            '/api/food-log/bulk-delete/',
            data='{"ids": [' + str(other_log.id) + ']}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        # Other user's log should NOT be deleted
        self.assertTrue(DailyLog.objects.filter(id=other_log.id).exists())


class ExerciseLogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='exerciseuser', password='testpass123')
        self.client.login(username='exerciseuser', password='testpass123')
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=80, sex='male', tdee=2500
        )
        WeightLog.objects.create(profile=self.profile, weight=80)

    def test_log_valid_exercise(self):
        res = self.client.post(
            '/api/exercise-log/',
            data='{"exercise_name": "Running (6 mph / 10 min mile)", "duration_minutes": 30}',
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['calories_burned'], 0)
        self.assertEqual(ExerciseLog.objects.count(), 1)

    def test_log_custom_exercise(self):
        res = self.client.post(
            '/api/exercise-log/',
            data='{"exercise_name": "Zorbing", "duration_minutes": 20, "notes": "fun"}',
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        log = ExerciseLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.exercise_name, 'Zorbing')

    def test_log_zero_duration_rejected(self):
        res = self.client.post(
            '/api/exercise-log/',
            data='{"exercise_name": "Walking (moderate, 3 mph)", "duration_minutes": 0}',
            content_type='application/json',
        )
        self.assertNotEqual(res.status_code, 200)
        self.assertEqual(ExerciseLog.objects.count(), 0)

    def test_log_missing_exercise_name_rejected(self):
        res = self.client.post(
            '/api/exercise-log/',
            data='{"duration_minutes": 30}',
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)

    def test_delete_exercise_log(self):
        log = ExerciseLog.objects.create(
            profile=self.profile,
            exercise_name='Yoga',
            duration_minutes=45,
            calories_burned=100,
        )
        res = self.client.delete(f'/api/exercise-log/{log.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ExerciseLog.objects.count(), 0)

    def test_grocery_list_route_removed(self):
        """The grocery list endpoint should no longer exist."""
        res = self.client.get('/api/grocery-list/')
        self.assertEqual(res.status_code, 404)

    def test_unauthenticated_exercise_log_redirects(self):
        self.client.logout()
        res = self.client.post(
            '/api/exercise-log/',
            data='{"exercise_name": "Yoga", "duration_minutes": 30}',
            content_type='application/json',
        )
        self.assertNotEqual(res.status_code, 200)


class TdeeAutoAdjustTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tdeeuser', password='testpass123')
        self.profile = FitnessProfile.objects.create(
            user=self.user, heightCm=175, weightKg=80, sex='male', tdee=2500
        )
        self.food = FoodItem.objects.create(
            name='Test Food', calories=100.0, protein=5.0, fat=2.0, carbs=10.0,
        )

    def _create_logs(self, days, daily_calories, weight_start, weight_end):
        """Helper: create food + weight logs over `days` days."""
        from datetime import timedelta
        today = timezone.localdate()
        for i in range(days):
            day = today - timedelta(days=days - 1 - i)
            # Food log
            quantity = daily_calories / 100.0  # food has 100 kcal per 100g → quantity = servings
            DailyLog.objects.create(profile=self.profile, food=self.food, quantity=quantity, date=day)
            # Weight log: auto_now_add ignores the date kwarg, so we set it via update
            w = weight_start + (weight_end - weight_start) * i / max(days - 1, 1)
            log = WeightLog.objects.create(profile=self.profile, weight=round(w, 2))
            WeightLog.objects.filter(pk=log.pk).update(date=day)

    def test_no_adjustment_with_insufficient_data(self):
        from core import utils
        # Only 3 weight logs, below the 7-log minimum
        for i in range(3):
            WeightLog.objects.create(profile=self.profile, weight=80)
        result = utils.auto_adjust_tdee(self.profile)
        self.assertEqual(result, 2500)
        self.assertIsNone(self.profile.tdee_override)

    def test_adjustment_when_losing_faster_than_expected(self):
        """If actual weight loss > predicted, TDEE is underestimated → should increase."""
        from core import utils
        # Eat 2000 kcal/day against a TDEE of 2500 → 500 kcal deficit → expect ~0.65 kg loss
        # Simulate losing 1.5 kg over 10 days (more than expected) → real TDEE must be higher
        self._create_logs(10, 2000, 80.0, 78.5)
        self.profile.refresh_from_db()
        result = utils.auto_adjust_tdee(self.profile)
        self.assertGreater(result, 2500)

    def test_adjustment_when_losing_slower_than_expected(self):
        """If actual weight loss < predicted, TDEE is overestimated → should decrease."""
        from core import utils
        # Eat 2000 kcal/day, TDEE 2500, expect ~0.65 kg loss over 10 days
        # Simulate only 0.05 kg loss → real TDEE must be lower
        self._create_logs(10, 2000, 80.0, 79.95)
        self.profile.refresh_from_db()
        result = utils.auto_adjust_tdee(self.profile)
        self.assertLess(result, 2500)

    def test_no_adjustment_when_trend_matches(self):
        """No adjustment when actual weight trend closely matches expected."""
        from core import utils
        # Eat 2000 kcal/day, TDEE 2500, expect ~0.065 kg/day × 10 days ≈ 0.65 kg loss
        # Simulate losing ~0.65 kg over 10 days (matches expectation)
        self._create_logs(10, 2000, 80.0, 79.35)
        result = utils.auto_adjust_tdee(self.profile)
        # Should not change TDEE (discrepancy < 150 kcal threshold)
        self.assertIsNone(self.profile.tdee_override)

    def test_effective_tdee_uses_override_when_set(self):
        self.profile.tdee_override = 2300
        self.profile.save()
        self.assertEqual(self.profile.get_effective_tdee(), 2300)

    def test_effective_tdee_falls_back_to_tdee(self):
        self.assertIsNone(self.profile.tdee_override)
        self.assertEqual(self.profile.get_effective_tdee(), 2500)


class FoodItemPortionSizeTests(TestCase):
    def test_food_item_default_portion_size(self):
        food = FoodItem.objects.create(name='Default Food', calories=100.0)
        self.assertEqual(food.portion_size, 100.0)
        self.assertEqual(food.unit, 'g')

    def test_food_item_custom_portion_size(self):
        food = FoodItem.objects.create(
            name='Custom Food', calories=50.0, portion_size=30.0, unit='oz'
        )
        self.assertEqual(food.portion_size, 30.0)
        self.assertEqual(food.unit, 'oz')


class BarcodeCacheTests(TestCase):
    """Tests for the 30-day barcode caching feature."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='barcodeuser', password='testpass123')
        self.client.login(username='barcodeuser', password='testpass123')

    # --- is_cache_valid helper ---

    def test_cache_valid_recent(self):
        from core import utils
        cached_at = timezone.now() - timezone.timedelta(days=1)
        self.assertTrue(utils.is_cache_valid(cached_at))

    def test_cache_valid_exactly_30_days(self):
        from core import utils
        # Exactly 30 days old is NOT valid (timedelta comparison is strict <)
        cached_at = timezone.now() - timezone.timedelta(days=30)
        self.assertFalse(utils.is_cache_valid(cached_at))

    def test_cache_invalid_expired(self):
        from core import utils
        cached_at = timezone.now() - timezone.timedelta(days=31)
        self.assertFalse(utils.is_cache_valid(cached_at))

    def test_cache_invalid_none(self):
        from core import utils
        self.assertFalse(utils.is_cache_valid(None))

    # --- lookup_barcode: local DB cache hit ---

    def test_lookup_barcode_cache_hit(self):
        from core import utils
        food = FoodItem.objects.create(
            name='Cached Food', barcode='111222333',
            calories=100.0, protein=5.0, carbs=10.0, fat=2.0,
            is_cached=True, cached_at=timezone.now() - timezone.timedelta(days=1)
        )
        result = utils.lookup_barcode('111222333')
        self.assertTrue(result['found'])
        self.assertEqual(result['source'], 'cache')
        self.assertEqual(result['data']['name'], 'Cached Food')
        self.assertEqual(result['data']['barcode'], '111222333')

    # --- lookup_barcode: barcode not found anywhere ---

    def test_lookup_barcode_not_found(self):
        from core import utils
        from unittest.mock import patch
        with patch('core.utils.readFoodData', return_value=None):
            result = utils.lookup_barcode('000000000000')
        self.assertFalse(result['found'])
        self.assertIsNone(result['source'])
        self.assertIsNone(result['data'])

    # --- lookup_barcode: cache miss → OFF API ---

    def test_lookup_barcode_cache_miss_calls_off(self):
        from core import utils
        from unittest.mock import patch
        mock_food = {
            'name': 'Test Bar',
            'category': 'Snacks',
            'allergens': [],
            'nutrients': {
                'calories_kcal': 200.0,
                'proteins_g': 4.0,
                'fat_g': 8.0,
                'carbohydrates_g': 30.0,
            },
            'micronutrients': {},
        }
        with patch('core.utils.readFoodData', return_value=mock_food) as mock_api:
            result = utils.lookup_barcode('999888777')
            mock_api.assert_called_once_with('999888777')
        self.assertTrue(result['found'])
        self.assertEqual(result['source'], 'off')
        self.assertEqual(result['data']['name'], 'Test Bar')
        # Should have been saved to DB
        self.assertTrue(FoodItem.objects.filter(barcode='999888777', is_cached=True).exists())

    # --- lookup_barcode: cache expired → re-fetches OFF API ---

    def test_lookup_barcode_cache_expired_refetches(self):
        from core import utils
        from unittest.mock import patch
        food = FoodItem.objects.create(
            name='Old Food', barcode='777666555',
            calories=50.0, protein=1.0, carbs=5.0, fat=1.0,
            is_cached=True, cached_at=timezone.now() - timezone.timedelta(days=31)
        )
        mock_food = {
            'name': 'Updated Food',
            'category': '',
            'allergens': [],
            'nutrients': {
                'calories_kcal': 110.0,
                'proteins_g': 3.0,
                'fat_g': 4.0,
                'carbohydrates_g': 15.0,
            },
            'micronutrients': {},
        }
        with patch('core.utils.readFoodData', return_value=mock_food) as mock_api:
            result = utils.lookup_barcode('777666555')
            mock_api.assert_called_once_with('777666555')
        self.assertTrue(result['found'])
        self.assertEqual(result['source'], 'off')
        self.assertEqual(result['data']['name'], 'Updated Food')
        food.refresh_from_db()
        # cached_at should be refreshed (within last minute)
        self.assertTrue(utils.is_cache_valid(food.cached_at))

    # --- OFF API response parsing ---

    def test_off_api_response_parsing(self):
        from core import utils
        product = {
            'product_name': 'Sample Cracker',
            'brands': 'BrandCo',
            'categories': 'Crackers',
            'allergens_tags': ['en:gluten'],
            'nutriments': {
                'energy-kcal_100g': 450.0,
                'proteins_100g': 8.0,
                'fat_100g': 18.0,
                'carbohydrates_100g': 62.0,
            }
        }
        parsed = utils.simplifyFoodData(product, 'test123')
        self.assertEqual(parsed['name'], 'Sample Cracker')
        self.assertAlmostEqual(parsed['nutrients']['calories_kcal'], 450.0)
        self.assertAlmostEqual(parsed['nutrients']['proteins_g'], 8.0)
        self.assertAlmostEqual(parsed['nutrients']['fat_g'], 18.0)
        self.assertAlmostEqual(parsed['nutrients']['carbohydrates_g'], 62.0)

    # --- API endpoint ---

    def test_search_barcode_endpoint_cache_hit(self):
        FoodItem.objects.create(
            name='Endpoint Food', barcode='ENDPOINT1',
            calories=200.0, protein=10.0, carbs=20.0, fat=5.0,
            is_cached=True, cached_at=timezone.now() - timezone.timedelta(days=1)
        )
        res = self.client.post(
            '/api/food/search-barcode/',
            data='{"barcode": "ENDPOINT1"}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['found'])
        self.assertEqual(data['source'], 'cache')
        self.assertEqual(data['data']['name'], 'Endpoint Food')

    def test_search_barcode_endpoint_missing_barcode(self):
        res = self.client.post(
            '/api/food/search-barcode/',
            data='{}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)

    def test_search_barcode_endpoint_not_found(self):
        from unittest.mock import patch
        with patch('core.utils.readFoodData', return_value=None):
            res = self.client.post(
                '/api/food/search-barcode/',
                data='{"barcode": "NOTEXIST999"}',
                content_type='application/json'
            )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data['found'])

    def test_search_barcode_endpoint_invalid_json(self):
        res = self.client.post(
            '/api/food/search-barcode/',
            data='not-json',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)

    def test_search_barcode_endpoint_method_not_allowed(self):
        res = self.client.get('/api/food/search-barcode/')
        self.assertEqual(res.status_code, 405)

