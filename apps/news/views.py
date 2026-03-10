from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import json

from .models import Article, Category, Source, SavedArticle, Collection, CollectionItem, UserFilter, Subscription
from .forms import ArticleSearchForm, CollectionForm


def index(request):
    """Главная страница с лентой новостей"""
    articles = Article.objects.filter(is_active=True).select_related('source', 'category')
    categories = Category.objects.all()
    sources = Source.objects.filter(is_active=True).annotate(articles_count=Count('articles'))
    
    # Фильтрация
    form = ArticleSearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data.get('query')
        category = form.cleaned_data.get('category')
        source = form.cleaned_data.get('source')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        if query:
            articles = articles.filter(
                Q(title__icontains=query) | 
                Q(content__icontains=query) |
                Q(excerpt__icontains=query)
            )
        if category:
            articles = articles.filter(category_id=category)
        if source:
            articles = articles.filter(source_id=source)
        if date_from:
            articles = articles.filter(published_at__gte=date_from)
        if date_to:
            articles = articles.filter(published_at__lte=date_to)
    
    # Фильтр по дате (быстрые кнопки)
    date_filter = request.GET.get('date')
    if date_filter == 'today':
        articles = articles.filter(published_at__date=timezone.now().date())
    elif date_filter == 'week':
        week_ago = timezone.now() - timedelta(days=7)
        articles = articles.filter(published_at__gte=week_ago)
    elif date_filter == 'month':
        month_ago = timezone.now() - timedelta(days=30)
        articles = articles.filter(published_at__gte=month_ago)
    
    # Сохранённые статьи пользователя (для отображения иконки)
    saved_ids = []
    if request.user.is_authenticated:
        saved_ids = SavedArticle.objects.filter(
            user=request.user
        ).values_list('article_id', flat=True)
    
    # Пагинация
    paginator = Paginator(articles, 10)
    page = request.GET.get('page', 1)
    articles_page = paginator.get_page(page)
    
    # Популярные теги (для облака)
    popular_tags = Article.objects.values('title').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    context = {
        'articles': articles_page,
        'categories': categories,
        'sources': sources,
        'form': form,
        'saved_ids': list(saved_ids),
        'popular_tags': popular_tags,
        'current_date_filter': date_filter,
    }
    return render(request, 'news/index.html', context)


def article_detail(request, pk):
    """Детальная страница статьи"""
    article = get_object_or_404(Article, pk=pk, is_active=True)
    article.increment_views()
    
    # Похожие статьи
    similar_articles = Article.objects.filter(
        Q(category=article.category) | Q(source=article.source)
    ).exclude(pk=article.pk).filter(is_active=True)[:5]
    
    saved = False
    if request.user.is_authenticated:
        saved = SavedArticle.objects.filter(
            user=request.user, article=article
        ).exists()
    
    context = {
        'article': article,
        'similar_articles': similar_articles,
        'saved': saved,
    }
    return render(request, 'news/article_detail.html', context)


@login_required
def save_article(request, pk):
    """Сохранение статьи в избранное"""
    article = get_object_or_404(Article, pk=pk)
    saved, created = SavedArticle.objects.get_or_create(
        user=request.user,
        article=article
    )
    
    if created:
        messages.success(request, 'Статья сохранена в избранное')
    else:
        saved.delete()
        messages.success(request, 'Статья удалена из избранного')
    
    # Если запрос через AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'saved': created,
            'message': 'Статья сохранена' if created else 'Статья удалена'
        })
    
    return redirect(request.META.get('HTTP_REFERER', 'news:index'))


@login_required
def saved_articles(request):
    """Список сохранённых статей"""
    saved = SavedArticle.objects.filter(
        user=request.user
    ).select_related('article', 'article__source').order_by('-saved_at')
    
    paginator = Paginator(saved, 10)
    page = request.GET.get('page', 1)
    saved_page = paginator.get_page(page)
    
    context = {
        'saved_articles': saved_page,
    }
    return render(request, 'news/saved_articles.html', context)


@login_required
def collections(request):
    """Список подборок пользователя"""
    collections = Collection.objects.filter(user=request.user).annotate(
        articles_count=Count('collectionitem')  # вместо 'articles'
    ).order_by('-created_at')
    
    context = {
        'collections': collections,
    }
    return render(request, 'news/collections.html', context)


@login_required
def collection_detail(request, pk):
    """Детальная страница подборки"""
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    items = collection.collectionitem_set.select_related('article', 'article__source').order_by('-added_at')
    
    context = {
        'collection': collection,
        'items': items,
    }
    return render(request, 'news/collection_detail.html', context)


@login_required
def create_collection(request):
    """Создание новой подборки"""
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.user = request.user
            collection.save()
            
            # Сохраняем данные фильтра, если есть
            filter_data = request.POST.get('filter_data')
            if filter_data:
                try:
                    collection.filter_data = json.loads(filter_data)
                except:
                    collection.filter_data = {}
                collection.save()
            
            messages.success(request, 'Подборка создана')
            return redirect('news:collection_detail', pk=collection.pk)
    else:
        form = CollectionForm()
        # Передаём данные фильтра из GET-параметров
        filter_data = request.GET.get('filter_data', '{}')
    
    context = {
        'form': form,
        'filter_data': filter_data,
    }
    return render(request, 'news/collection_form.html', context)


@login_required
def add_to_collection(request):
    """Добавление статьи в подборку"""
    if request.method == 'POST':
        article_id = request.POST.get('article_id')
        collection_id = request.POST.get('collection_id')
        
        article = get_object_or_404(Article, pk=article_id)
        collection = get_object_or_404(Collection, pk=collection_id, user=request.user)
        
        item, created = CollectionItem.objects.get_or_create(
            collection=collection,
            article=article
        )
        
        if created:
            messages.success(request, f'Статья добавлена в подборку "{collection.name}"')
        else:
            messages.info(request, f'Статья уже есть в подборке "{collection.name}"')
        
        return redirect('news:article_detail', pk=article_id)
    
    return redirect('news:index')


@login_required
def remove_from_collection(request, collection_id, article_id):
    """Удаление статьи из подборки"""
    collection = get_object_or_404(Collection, pk=collection_id, user=request.user)
    article = get_object_or_404(Article, pk=article_id)
    
    CollectionItem.objects.filter(
        collection=collection,
        article=article
    ).delete()
    
    messages.success(request, f'Статья удалена из подборки "{collection.name}"')
    return redirect('news:collection_detail', pk=collection_id)


@login_required
def delete_collection(request, pk):
    """Удаление подборки"""
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    collection.delete()
    messages.success(request, 'Подборка удалена')
    return redirect('news:collections')


@login_required
def save_filter(request):
    """Сохранение текущего фильтра"""
    if request.method == 'POST':
        name = request.POST.get('name')
        filter_data = request.POST.get('filter_data')
        
        if name and filter_data:
            # Преобразуем строку запроса в словарь
            from urllib.parse import parse_qs
            filter_dict = parse_qs(filter_data)
            # Преобразуем значения из списков в строки
            for key in filter_dict:
                filter_dict[key] = filter_dict[key][0] if filter_dict[key] else ''
            
            UserFilter.objects.create(
                user=request.user,
                name=name,
                filter_data=filter_dict
            )
            messages.success(request, 'Фильтр сохранён')
        else:
            messages.error(request, 'Ошибка при сохранении фильтра')
    
    return redirect(request.META.get('HTTP_REFERER', 'news:index'))


@login_required
def subscribe(request):
    """Подписка на обновления по фильтру"""
    if request.method == 'POST':
        filter_data = request.POST.get('filter_data', '')
        email_digest = request.POST.get('email_digest') == 'on'
        push_notifications = request.POST.get('push_notifications') == 'on'
        
        # Парсим параметры фильтра
        from urllib.parse import parse_qs
        try:
            if filter_data.startswith('{'):
                filter_dict = json.loads(filter_data)
            else:
                filter_dict = parse_qs(filter_data)
                for key in filter_dict:
                    filter_dict[key] = filter_dict[key][0] if filter_dict[key] else ''
        except:
            filter_dict = {}
        
        # Создаём подписку
        subscription = Subscription.objects.create(
            user=request.user,
            filter_data=filter_dict,
            email_digest=email_digest,
            push_notifications=push_notifications
        )
        
        messages.success(request, 'Вы успешно подписались на обновления')
        return redirect(request.META.get('HTTP_REFERER', 'news:index'))
    
    return redirect('news:index')


def sources(request):
    """Список источников новостей"""
    # Простой запрос - получаем все активные источники
    sources = Source.objects.filter(is_active=True).order_by('name')
    
    # Получаем все категории (просто для отображения)
    categories = Category.objects.all()
    
    context = {
        'sources': sources,
        'categories': categories,
    }
    return render(request, 'news/sources.html', context)


def source_detail(request, pk):
    """Статьи из конкретного источника"""
    source = get_object_or_404(Source, pk=pk, is_active=True)
    articles = Article.objects.filter(
        source=source, is_active=True
    ).select_related('category').order_by('-published_at')
    
    paginator = Paginator(articles, 10)
    page = request.GET.get('page', 1)
    articles_page = paginator.get_page(page)
    
    context = {
        'source': source,
        'articles': articles_page,
    }
    return render(request, 'news/source_detail.html', context)


def search_suggestions(request):
    """AJAX-поиск подсказок"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    articles = Article.objects.filter(
        Q(title__icontains=query) | Q(excerpt__icontains=query),
        is_active=True
    ).select_related('source')[:5]
    
    suggestions = []
    for article in articles:
        suggestions.append({
            'id': article.id,
            'title': article.title,
            'source': article.source.name,
            'url': article.get_absolute_url(),
            'image': article.image_url or '',
            'date': article.published_at.strftime('%d.%m.%Y')
        })
    
    return JsonResponse({'suggestions': suggestions})
    
def custom_404(request, exception):
    """Кастомная страница 404"""
    return render(request, 'errors/404.html', status=404)

def custom_500(request):
    """Кастомная страница 500"""
    return render(request, 'errors/500.html', status=500)