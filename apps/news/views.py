from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test
import json

from .models import Article, Category, Source, SavedArticle, UserFilter, Subscription, Comment
from .forms import ArticleSearchForm, CommentForm


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

def admin_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(admin_required)
def sources(request):
    """Список источников новостей (только для админов)"""
    sources = Source.objects.filter(is_active=True).order_by('name')
    categories = Category.objects.all()
    
    context = {
        'sources': sources,
        'categories': categories,
    }
    return render(request, 'news/sources.html', context)

@user_passes_test(admin_required)
def source_detail(request, pk):
    """Статьи из конкретного источника (только для админов)"""
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


@login_required
def add_comment(request, article_id):
    """Добавление комментария к статье"""
    article = get_object_or_404(Article, pk=article_id, is_active=True)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.user = request.user
            comment.save()
            
            # Проверяем, были ли замены в тексте
            warnings = getattr(form, 'warnings', [])
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'text': comment.text,
                        'user': comment.user.username,
                        'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
                        'is_edited': comment.is_edited,
                        'warnings': warnings
                    }
                })
            
            if warnings:
                messages.warning(request, ' '.join(warnings))
            else:
                messages.success(request, 'Комментарий добавлен')
            
            return redirect('news:article_detail', pk=article_id)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    
    return redirect('news:article_detail', pk=article_id)

@login_required
def edit_comment(request, comment_id):
    """Редактирование комментария"""
    comment = get_object_or_404(Comment, pk=comment_id, user=request.user)
    
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.is_edited = True
            comment.save()
            
            messages.success(request, 'Комментарий обновлён')
            return redirect('news:article_detail', pk=comment.article.pk)
    
    return redirect('news:article_detail', pk=comment.article.pk)

@login_required
def delete_comment(request, comment_id):
    """Удаление комментария"""
    comment = get_object_or_404(Comment, pk=comment_id, user=request.user)
    article_id = comment.article.pk
    
    comment.delete()
    messages.success(request, 'Комментарий удалён')
    
    return redirect('news:article_detail', pk=article_id)