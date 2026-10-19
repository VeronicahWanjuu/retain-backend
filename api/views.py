from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Budget, Category, Expense, default_category
from .serializers import (
    BudgetSerializer, CategorySerializer, ExpenseSerializer,
    RegisterSerializer, UserSerializer,
)

SORT_OPTIONS = {'date', '-date', 'amount', '-amount'}


class ExpensePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


def month_and_year(request):
    """Read ?month=&year= from the url, default to this month."""
    today = date.today()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
    except ValueError:
        raise ValidationError('month and year must be numbers.')
    if not 1 <= month <= 12:
        raise ValidationError('month must be between 1 and 12.')
    return month, year


# ---------- AUTH ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(s.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_me(request):
    return Response(UserSerializer(request.user).data)


# ---------- CATEGORIES ----------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def categories(request):
    if request.method == 'GET':
        return Response(CategorySerializer(Category.objects.all(), many=True).data)

    if not request.user.is_staff:
        return Response({'detail': 'Admins only.'}, status=status.HTTP_403_FORBIDDEN)
    s = CategorySerializer(data=request.data)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(s.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def category_detail(request, pk):
    cat = Category.objects.filter(pk=pk).first()
    if cat is None:
        return Response({'detail': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

    if cat.name == 'Uncategorized':
        return Response(
            {'detail': 'Uncategorized is the safety net, it cannot be changed or deleted.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == 'DELETE':
        # move the expenses first so nobody loses their data
        Expense.objects.filter(category=cat).update(category=default_category())
        cat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    s = CategorySerializer(cat, data=request.data)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(s.data)


# ---------- EXPENSES ----------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def expenses(request):
    if request.method == 'POST':
        s = ExpenseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        cat = s.validated_data.get('category') or default_category()
        s.save(user=request.user, category=cat)
        return Response(s.data, status=status.HTTP_201_CREATED)

    # only ever my own expenses
    items = Expense.objects.filter(user=request.user).select_related('category')
    p = request.GET

    if p.get('category'):
        if not p['category'].isdigit():
            raise ValidationError({'category': 'must be a category id.'})
        items = items.filter(category_id=int(p['category']))

    if p.get('payment_method'):
        items = items.filter(payment_method=p['payment_method'])

    for key, lookup in (('start_date', 'date__gte'), ('end_date', 'date__lte')):
        if p.get(key):
            try:
                parsed = parse_date(p[key])
            except ValueError:
                parsed = None
            if parsed is None:
                raise ValidationError({key: 'use the format YYYY-MM-DD.'})
            items = items.filter(**{lookup: parsed})

    for key, lookup in (('min_amount', 'amount__gte'), ('max_amount', 'amount__lte')):
        if p.get(key):
            try:
                number = Decimal(p[key])
            except InvalidOperation:
                raise ValidationError({key: 'must be a number.'})
            if not number.is_finite():
                raise ValidationError({key: 'must be a number.'})
            items = items.filter(**{lookup: number})

    if p.get('search'):
        items = items.filter(title__icontains=p['search'])

    sort = p.get('sort', '-date')
    if sort not in SORT_OPTIONS:
        raise ValidationError({'sort': 'use date, -date, amount or -amount.'})
    items = items.order_by(sort, '-id')

    paginator = ExpensePagination()
    page = paginator.paginate_queryset(items, request)
    return paginator.get_paginated_response(ExpenseSerializer(page, many=True).data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def expense_detail(request, pk):
    item = Expense.objects.filter(pk=pk, user=request.user).select_related('category').first()
    if item is None:
        # same answer whether it doesn't exist or belongs to someone else
        return Response({'detail': 'Expense not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(ExpenseSerializer(item).data)

    if request.method == 'PUT':
        s = ExpenseSerializer(item, data=request.data)
        s.is_valid(raise_exception=True)
        cat = s.validated_data.get('category') or default_category()
        s.save(category=cat)
        return Response(s.data)

    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- BUDGET ----------
@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def budget(request):
    month, year = month_and_year(request)

    if request.method == 'GET':
        b = Budget.objects.filter(user=request.user, month=month, year=year).first()
        if b is None:
            return Response({'amount': 0, 'month': month, 'year': year})
        return Response(BudgetSerializer(b).data)

    s = BudgetSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    b, _ = Budget.objects.update_or_create(
        user=request.user, month=month, year=year,
        defaults={'amount': s.validated_data['amount']},
    )
    return Response(BudgetSerializer(b).data)


# ---------- USER DASHBOARD ----------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    month, year = month_and_year(request)
    items = Expense.objects.filter(
        user=request.user, date__month=month, date__year=year
    ).select_related('category')

    total_spent = float(items.aggregate(t=Sum('amount'))['t'] or 0)
    b = Budget.objects.filter(user=request.user, month=month, year=year).first()
    budget_amount = float(b.amount) if b else 0
    remaining = budget_amount - total_spent
    percent_used = round(total_spent / budget_amount * 100, 1) if budget_amount else 0

    # orange at 80%, red at 100%
    if budget_amount == 0:
        label = 'no budget'
    elif total_spent >= budget_amount:
        label = 'over budget'
    elif percent_used >= 80:
        label = 'approaching budget'
    else:
        label = 'within budget'

    rows = items.values('category__name').annotate(total=Sum('amount')).order_by('-total')
    by_category = [
        {'name': r['category__name'] or 'Uncategorized', 'total': float(r['total'])}
        for r in rows
    ]
    highest = items.order_by('-amount').first()

    return Response({
        'month': month,
        'year': year,
        'total_spent': total_spent,
        'budget': budget_amount,
        'remaining': remaining,
        'percent_used': percent_used,
        'status': label,
        'highest_expense': ExpenseSerializer(highest).data if highest else None,
        'by_category': by_category,
        'recent_expenses': ExpenseSerializer(items.order_by('-date', '-id')[:5], many=True).data,
    })


# ---------- ADMIN DASHBOARD ----------
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard(request):
    today = date.today()

    # every category, including the ones nobody has used yet
    cats = Category.objects.annotate(count=Count('expense'), total=Sum('expense__amount'))
    rows = [
        {'id': c.id, 'name': c.name, 'count': c.count, 'total': float(c.total or 0)}
        for c in cats
    ]
    top5 = sorted(rows, key=lambda r: (-r['count'], r['name']))[:5]
    bottom5 = sorted(rows, key=lambda r: (r['count'], r['name']))[:5]

    return Response({
        'total_users': User.objects.count(),
        'total_expenses': Expense.objects.count(),
        'total_value': float(Expense.objects.aggregate(t=Sum('amount'))['t'] or 0),
        'this_month_count': Expense.objects.filter(
            date__month=today.month, date__year=today.year
        ).count(),
        'by_category': sorted(rows, key=lambda r: -r['total']),
        'top5_categories': top5,
        'bottom5_categories': bottom5,
        'recent_expenses': ExpenseSerializer(
            Expense.objects.select_related('category', 'user').order_by('-created_at')[:10],
            many=True,
        ).data,
        'recent_users': UserSerializer(User.objects.order_by('-date_joined')[:10], many=True).data,
    })