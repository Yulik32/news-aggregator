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
    
    name = models.CharField(
        max_length=200, 
        verbose_name='Название источника',
        help_text='Например: Лента.ру, РИА Новости, Хабр'
    )
    url = models.URLField(
        verbose_name='URL источника',
        help_text='Ссылка на RSS-ленту или главную страницу'
    )
    source_type = models.CharField(
        max_length=10, 
        choices=SOURCE_TYPES, 
        default='rss',
        verbose_name='Тип источника'
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sources',
        verbose_name='Категория',
        help_text='Основная категория новостей из этого источника'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Отметьте, если источник должен участвовать в парсинге'
    )
    last_parsed = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Последний парсинг'
    )
    parse_error = models.TextField(
        blank=True,
        verbose_name='Ошибка парсинга',
        help_text='Последняя ошибка при парсинге (заполняется автоматически)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Источник'
        verbose_name_plural = 'Источники'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=500, verbose_name='Заголовок статьи')
    content = models.TextField(verbose_name='Текст статьи')
    excerpt = models.TextField(
        max_length=500, 
        blank=True, 
        verbose_name='Краткое описание',
        help_text='Короткое описание для превью на главной странице (до 500 символов)'
    )
    source = models.ForeignKey(
        Source, 
        on_delete=models.CASCADE, 
        related_name='articles', 
        verbose_name='Источник',
        null=True,
        blank=True,
        help_text='Если это ваша собственная статья, оставьте пустым'
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='articles', 
        verbose_name='Категория'
    )
    url = models.URLField(
        unique=True, 
        blank=True, 
        null=True,
        verbose_name='Ссылка на оригинал',
        help_text='Если это ваша собственная статья, оставьте пустым'
    )
    image = models.ImageField(
        upload_to='articles/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='Изображение статьи',
        help_text='Загрузите изображение с компьютера'
    )
    image_url = models.URLField(
        blank=True, 
        verbose_name='URL изображения',
        help_text='Или укажите ссылку на изображение в интернете'
    )
    published_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Дата публикации'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    views = models.PositiveIntegerField(
        default=0, 
        verbose_name='Просмотры'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Опубликовать на сайте',
        help_text='Снимите галочку, чтобы сохранить как черновик'
    )
    
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

class Comment(models.Model):
    """Модель комментариев к статьям"""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(verbose_name='Текст комментария')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    is_approved = models.BooleanField(default=True, verbose_name='Одобрен')
    is_edited = models.BooleanField(default=False, verbose_name='Отредактирован')
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Комментарий от {self.user.username} к {self.article.title[:30]}"