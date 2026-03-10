import feedparser
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.news.models import Source, Article, Category
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Парсинг RSS-лент источников для наполнения сайта новостями'
    
    def add_arguments(self, parser):
        parser.add_argument('--source', type=int, help='ID конкретного источника для парсинга')
        parser.add_argument('--all', action='store_true', help='Парсить все активные источники')
        parser.add_argument('--proxy', type=str, help='Прокси-сервер (например: http://user:pass@host:port)')
    
    def setup_proxy(self, proxy_url):
        """Настройка прокси для urllib"""
        if proxy_url:
            self.stdout.write(f"[ПРОКСИ] Используется прокси: {proxy_url}")
            proxy_handler = urllib.request.ProxyHandler({
                'http': proxy_url,
                'https': proxy_url
            })
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
            return True
        return False
    
    def fetch_rss(self, url, proxy_url=None):
        """Загрузка RSS с поддержкой прокси"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        try:
            if proxy_url:
                proxy_handler = urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
                opener = urllib.request.build_opener(proxy_handler)
                return opener.open(req, timeout=30).read()
            else:
                return urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ОШИБКА] Ошибка загрузки RSS: {e}"))
            return None
    
    def handle(self, *args, **options):
        proxy_url = options.get('proxy')
        
        # Настраиваем прокси если указан
        if proxy_url:
            self.setup_proxy(proxy_url)
        
        # Получаем источники для парсинга
        if options.get('source'):
            sources = Source.objects.filter(pk=options['source'], is_active=True)
        else:
            sources = Source.objects.filter(is_active=True, source_type='rss')
        
        if not sources.exists():
            self.stdout.write(self.style.WARNING("[ВНИМАНИЕ] Нет активных RSS-источников для парсинга"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"[ИНФО] Найдено источников для парсинга: {sources.count()}"))
        
        total_new = 0
        for source in sources:
            self.stdout.write(f"\n[ПАРСИНГ] {source.name} ({source.url})...")
            
            try:
                # Загружаем RSS
                rss_data = self.fetch_rss(source.url, proxy_url)
                if not rss_data:
                    continue
                
                feed = feedparser.parse(rss_data)
                new_count = 0
                
                if feed.bozo and not isinstance(feed.bozo_exception, feedparser.CharacterEncodingOverride):
                    self.stdout.write(self.style.WARNING(
                        f"[ПРЕДУПРЕЖДЕНИЕ] {source.name}: {feed.bozo_exception}"
                    ))
                
                for entry in feed.entries[:30]:  # Ограничиваем 30 последними записями
                    # Проверяем, есть ли уже такая статья
                    if Article.objects.filter(url=entry.link).exists():
                        continue
                    
                    # Извлекаем описание
                    description = entry.get('description', '')
                    if description:
                        soup = BeautifulSoup(description, 'html.parser')
                        description = soup.get_text()[:500]
                    
                    # Извлекаем контент
                    content = ''
                    if hasattr(entry, 'content'):
                        content = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    else:
                        content = description
                    
                    soup = BeautifulSoup(content, 'html.parser')
                    content = soup.get_text()
                    
                    # Извлекаем изображение
                    image_url = ''
                    if hasattr(entry, 'media_content'):
                        image_url = entry.media_content[0].get('url', '')
                    elif hasattr(entry, 'links'):
                        for link in entry.links:
                            if link.get('type', '').startswith('image'):
                                image_url = link.href
                                break
                    
                    # Определяем категорию
                    category = source.category
                    if hasattr(entry, 'tags') and entry.tags:
                        for tag in entry.tags[:1]:
                            tag_term = tag.term[:100]
                            
                            # Создаем уникальный slug
                            base_slug = tag_term.lower().replace(' ', '-')[:50]
                            slug = base_slug
                            counter = 1
                            
                            while Category.objects.filter(slug=slug).exists():
                                slug = f"{base_slug}-{counter}"
                                counter += 1
                            
                            cat, created = Category.objects.get_or_create(
                                name=tag_term,
                                defaults={'slug': slug}
                            )
                            category = cat
                            break
                    
                    # Дата публикации
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6])
                    else:
                        published = timezone.now()
                    
                    if timezone.is_naive(published):
                        published = timezone.make_aware(published)
                    
                    # Создаём статью
                    Article.objects.create(
                        title=entry.title,
                        content=content[:10000],
                        excerpt=description[:500],
                        source=source,
                        category=category,
                        url=entry.link,
                        image_url=image_url,
                        published_at=published,
                    )
                    new_count += 1
                
                source.last_parsed = timezone.now()
                source.parse_error = ''
                source.save()
                
                total_new += new_count
                self.stdout.write(self.style.SUCCESS(
                    f"[ГОТОВО] Добавлено {new_count} новых статей из {source.name}"
                ))
                
            except Exception as e:
                source.parse_error = str(e)
                source.save()
                self.stdout.write(self.style.ERROR(
                    f"[ОШИБКА] При парсинге {source.name}: {e}"
                ))
                logger.error(f"Error parsing {source.name}: {e}", exc_info=True)
        
        self.stdout.write(self.style.SUCCESS(f"\n[ИТОГО] Всего добавлено новых статей: {total_new}"))