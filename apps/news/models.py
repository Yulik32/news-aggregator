from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True)
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
    
    def __str__(self):
        return self.name

class Source(models.Model):
    SOURCE_TYPES = [
        ('rss', 'RSS-лента'),
        ('manual', 'Ручное добавление'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название')
    url = models.URLField(verbose_name='URL источника')
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default='rss')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='sources')
    is_active = models.BooleanField(default=True)
    last_parsed = models.DateTimeField(null=True, blank=True)
    parse_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Источник'
        verbose_name_plural = 'Источники'
    
    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=500, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Содержание')
    excerpt = models.TextField(max_length=500, blank=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='articles')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='articles')
    url = models.URLField(unique=True)
    image_url = models.URLField(blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-published_at']
    
    def __str__(self):
        return self.title
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

class SavedArticle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_articles')
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'article']
        verbose_name = 'Сохранённая статья'
        verbose_name_plural = 'Сохранённые статьи'
    
    def __str__(self):
        return f"{self.user.username} - {self.article.title}"

class Collection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    filter_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Подборка'
        verbose_name_plural = 'Подборки'
    
    def __str__(self):
        return self.name

class CollectionItem(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['collection', 'article']
        verbose_name = 'Элемент подборки'
        verbose_name_plural = 'Элементы подборки'

# ДОБАВЛЯЕМ НЕДОСТАЮЩИЕ МОДЕЛИ:

class UserFilter(models.Model):
    """Сохранённый фильтр пользователя"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_filters')
    name = models.CharField(max_length=200, verbose_name='Название')
    filter_data = models.JSONField(verbose_name='Данные фильтра')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Сохранённый фильтр'
        verbose_name_plural = 'Сохранённые фильтры'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"

class Subscription(models.Model):
    """Подписка пользователя на фильтр"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    filter_data = models.JSONField(verbose_name='Данные фильтра')
    email_digest = models.BooleanField(default=False, verbose_name='Email-дайджест')
    push_notifications = models.BooleanField(default=False, verbose_name='Push-уведомления')
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True, verbose_name='Последняя отправка')
    
    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - Подписка #{self.id}"
    
class NewsletterSubscription(models.Model):
    """Подписка на email-рассылку"""
    email = models.EmailField(unique=True, verbose_name='Email')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='newsletter_subscriptions')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подписки')
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отписки')
    
    # Настройки рассылки
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Ежедневно'),
            ('weekly', 'Еженедельно'),
            ('never', 'Никогда')
        ],
        default='daily',
        verbose_name='Частота'
    )
    
    # Категории для дайджеста
    categories = models.ManyToManyField('Category', blank=True, verbose_name='Категории')
    
    class Meta:
        verbose_name = 'Подписка на рассылку'
        verbose_name_plural = 'Подписки на рассылку'
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return self.email