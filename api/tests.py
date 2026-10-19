from datetime import date

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Budget, Category, Expense, default_category

STRONG = 'Kuku#Pass2024'


class BaseCase(APITestCase):
    def setUp(self):
        self.food = Category.objects.create(name='Food')
        self.fare = Category.objects.create(name='Transport')
        self.unc = default_category()
        self.amina = User.objects.create_user('amina', 'amina@test.com', STRONG)
        self.brian = User.objects.create_user('brian', 'brian@test.com', STRONG)
        self.admin = User.objects.create_user('boss', 'boss@test.com', STRONG, is_staff=True)

    def login(self, user):
        self.client.force_authenticate(user=user)

    def add(self, user, title='Lunch', amount='200', cat=None, pay='cash'):
        return Expense.objects.create(
            user=user, title=title, amount=amount,
            category=cat or self.food, date=date.today(), payment_method=pay,
        )


class AuthTests(BaseCase):
    def test_register_then_login(self):
        r = self.client.post('/api/auth/register/', {
            'username': 'wanjiku', 'email': 'w@test.com', 'password': STRONG})
        self.assertEqual(r.status_code, 201)
        r = self.client.post('/api/auth/login/', {'username': 'wanjiku', 'password': STRONG})
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)

    def test_weak_password_rejected(self):
        r = self.client.post('/api/auth/register/', {
            'username': 'x1', 'email': 'x@test.com', 'password': '123'})
        self.assertEqual(r.status_code, 400)

    def test_me_shows_role(self):
        self.login(self.admin)
        self.assertEqual(self.client.get('/api/auth/me/').data['role'], 'admin')
        self.login(self.amina)
        self.assertEqual(self.client.get('/api/auth/me/').data['role'], 'user')


class ExpenseTests(BaseCase):
    def test_needs_login(self):
        self.assertEqual(self.client.get('/api/expenses/').status_code, 401)

    def test_users_only_see_own_expenses(self):
        self.add(self.amina, 'Amina lunch')
        self.add(self.brian, 'Brian lunch')
        self.login(self.amina)
        r = self.client.get('/api/expenses/')
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['title'], 'Amina lunch')

    def test_cannot_touch_someone_elses_expense(self):
        e = self.add(self.brian)
        self.login(self.amina)
        self.assertEqual(self.client.get(f'/api/expenses/{e.id}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/expenses/{e.id}/').status_code, 404)

    def test_negative_amount_rejected(self):
        self.login(self.amina)
        r = self.client.post('/api/expenses/', {
            'title': 'Bad', 'amount': '-5', 'date': str(date.today())})
        self.assertEqual(r.status_code, 400)

    def test_missing_category_becomes_uncategorized(self):
        self.login(self.amina)
        r = self.client.post('/api/expenses/', {
            'title': 'Chips', 'amount': '50', 'date': str(date.today())})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['category_name'], 'Uncategorized')

    def test_filters_and_sort(self):
        self.add(self.amina, 'Matatu fare', '100', self.fare)
        self.add(self.amina, 'Chips and sausage', '300', self.food)
        self.add(self.amina, 'Textbook', '1500', self.food, pay='card')
        self.login(self.amina)
        self.assertEqual(self.client.get('/api/expenses/', {'search': 'matatu'}).data['count'], 1)
        self.assertEqual(self.client.get('/api/expenses/', {'category': self.food.id}).data['count'], 2)
        self.assertEqual(self.client.get('/api/expenses/', {'payment_method': 'card'}).data['count'], 1)
        r = self.client.get('/api/expenses/', {'min_amount': '200', 'max_amount': '400'})
        self.assertEqual(r.data['count'], 1)
        r = self.client.get('/api/expenses/', {'sort': '-amount'})
        self.assertEqual(r.data['results'][0]['title'], 'Textbook')

    def test_bad_filters_return_400(self):
        self.login(self.amina)
        for params in ({'category': 'abc'}, {'min_amount': 'lots'},
                       {'start_date': 'yesterday'}, {'sort': 'banana'}):
            r = self.client.get('/api/expenses/', params)
            self.assertEqual(r.status_code, 400, params)

    def test_pagination(self):
        for i in range(12):
            self.add(self.amina, f'Item {i}')
        self.login(self.amina)
        r = self.client.get('/api/expenses/')
        self.assertEqual(r.data['count'], 12)
        self.assertEqual(len(r.data['results']), 10)
        self.assertIsNotNone(r.data['next'])
        self.assertEqual(len(self.client.get('/api/expenses/', {'page': 2}).data['results']), 2)

    def test_budget_and_dashboard_status(self):
        self.login(self.amina)
        self.assertEqual(self.client.post('/api/budget/', {'amount': '1000'}).status_code, 200)
        self.assertEqual(self.client.get('/api/dashboard/').data['status'], 'within budget')

        self.add(self.amina, 'Rent bit', '850')
        d = self.client.get('/api/dashboard/').data
        self.assertEqual(d['status'], 'approaching budget')
        self.assertEqual(d['remaining'], 150)

        self.add(self.amina, 'Party', '300')
        d = self.client.get('/api/dashboard/').data
        self.assertEqual(d['status'], 'over budget')
        self.assertEqual(d['remaining'], -150)

        # saving again updates, it does not create a second budget
        self.client.put('/api/budget/', {'amount': '1200'})
        self.assertEqual(Budget.objects.filter(user=self.amina).count(), 1)


class AdminTests(BaseCase):
    def test_normal_user_blocked(self):
        self.login(self.amina)
        self.assertEqual(self.client.get('/api/admin-dashboard/').status_code, 403)
        self.assertEqual(self.client.post('/api/categories/', {'name': 'Hacks'}).status_code, 403)

    def test_admin_creates_and_renames_category(self):
        self.login(self.admin)
        r = self.client.post('/api/categories/', {'name': 'Airtime'})
        self.assertEqual(r.status_code, 201)
        r2 = self.client.put(f"/api/categories/{r.data['id']}/", {'name': 'Data bundles'})
        self.assertEqual(r2.data['name'], 'Data bundles')

    def test_duplicate_category_rejected(self):
        self.login(self.admin)
        self.assertEqual(self.client.post('/api/categories/', {'name': 'Food'}).status_code, 400)

    def test_delete_category_moves_expenses(self):
        e = self.add(self.amina, 'Lunch', '100', self.food)
        self.login(self.admin)
        self.assertEqual(self.client.delete(f'/api/categories/{self.food.id}/').status_code, 204)
        e.refresh_from_db()
        self.assertEqual(e.category.name, 'Uncategorized')

    def test_cannot_delete_uncategorized(self):
        self.login(self.admin)
        self.assertEqual(self.client.delete(f'/api/categories/{self.unc.id}/').status_code, 400)

    def test_admin_dashboard_numbers(self):
        self.add(self.amina, 'a', '100', self.food)
        self.add(self.amina, 'b', '200', self.food)
        self.add(self.brian, 'c', '50', self.fare)
        self.login(self.admin)
        d = self.client.get('/api/admin-dashboard/').data
        self.assertEqual(d['total_users'], 3)
        self.assertEqual(d['total_expenses'], 3)
        self.assertEqual(d['total_value'], 350)
        self.assertEqual(d['this_month_count'], 3)
        self.assertEqual(d['top5_categories'][0]['name'], 'Food')
        self.assertEqual(d['bottom5_categories'][0]['count'], 0)