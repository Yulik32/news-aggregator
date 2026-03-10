from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Category, Source, Article, SavedArticle, Collection, CollectionItem, UserFilter, Subscription

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'articles_count_badge']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_per_page = 20
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(articles_count=Count('articles'))
    
    def articles_count_badge(self, obj):
        count = getattr(obj, 'articles_count', 0)
        return format_html(
            '<span style="background: linear-gradient(135deg, #4361ee, #3a0ca3); color: white; padding: 3px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;">📊 {}</span>',
            count
        )
    articles_count_badge.short_description = 'Статей'
    articles_count_badge.admin_order_field = 'articles_count'

# Остальные классы пока оставляем без изменений (как в предыдущем упрощенном варианте)
@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'category', 'is_active', 'last_parsed']
    list_filter = ['source_type', 'is_active', 'category']
    search_fields = ['name', 'url']
    list_per_page = 20
    list_editable = ['is_active']

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'category', 'is_active', 'published_at', 'views']
    list_filter = ['source', 'category', 'is_active', 'published_at']
    search_fields = ['title', 'content']
    readonly_fields = ['views', 'created_at']
    date_hierarchy = 'published_at'
    list_per_page = 20
    list_editable = ['is_active']
    
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'✅ {updated} статей отмечено как активные')
    mark_active.short_description = 'Отметить как активные'
    
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'❌ {updated} статей отмечено как неактивные')
    mark_inactive.short_description = 'Отметить как неактивные'
    
    actions = ['mark_active', 'mark_inactive']

@admin.register(SavedArticle)
class SavedArticleAdmin(admin.ModelAdmin):
    list_display = ['user', 'article', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['user__username', 'article__title']
    list_per_page = 20

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'user__username']
    list_per_page = 20
    list_editable = ['is_public']

@admin.register(CollectionItem)
class CollectionItemAdmin(admin.ModelAdmin):
    list_display = ['collection', 'article', 'added_at']
    list_filter = ['added_at']
    list_per_page = 20

@admin.register(UserFilter)
class UserFilterAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'user__username']
    list_per_page = 20

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_digest', 'push_notifications', 'created_at']
    list_filter = ['email_digest', 'push_notifications', 'created_at']
    search_fields = ['user__username']
    list_per_page = 20
    list_editable = ['email_digest', 'push_notifications']