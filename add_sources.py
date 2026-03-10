import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'news_aggregator.settings')
django.setup()

from apps.news.models import Source, Category

# Создаем категории если их нет
categories = {
    'Политика': 'politics',
    'Экономика': 'economy',
    'Технологии': 'tech',
    'Наука': 'science',
    'Спорт': 'sport',
    'Культура': 'culture',
}

for cat_name, cat_slug in categories.items():
    Category.objects.get_or_create(name=cat_name, defaults={'slug': cat_slug})

# RSS-источники
rss_sources = [
    {
        'name': 'Лента.ру',
        'url': 'https://lenta.ru/rss',
        'category': 'Политика',
    },
    {
        'name': 'РИА Новости',
        'url': 'https://ria.ru/export/rss2/index.xml',
        'category': 'Политика',
    },
    {
        'name': 'Вести.ру',
        'url': 'http://www.vesti.ru/vesti.rss',
        'category': 'Политика',
    },
    {
        'name': 'Коммерсантъ',
        'url': 'https://www.kommersant.ru/RSS/main.xml',
        'category': 'Экономика',
    },
    {
        'name': 'РБК',
        'url': 'http://static.feed.rbc.ru/rbc/logical/footer/news.rss',
        'category': 'Экономика',
    },
    {
        'name': 'Хабр',
        'url': 'https://habr.com/ru/rss/all/',
        'category': 'Технологии',
    },
    {
        'name': 'TJournal',
        'url': 'https://tjournal.ru/rss',
        'category': 'Технологии',
    },
    {
        'name': 'BBC Russian',
        'url': 'http://feeds.bbci.co.uk/russian/rss.xml',
        'category': 'Политика',
    },
    {
        'name': 'Euronews',
        'url': 'https://ru.euronews.com/rss',
        'category': 'Политика',
    },
    {
        'name': 'Наука и жизнь',
        'url': 'https://www.nkj.ru/rss/',
        'category': 'Наука',
    },
]

# Добавляем источники
for source_data in rss_sources:
    category = Category.objects.get(name=source_data['category'])
    source, created = Source.objects.get_or_create(
        url=source_data['url'],
        defaults={
            'name': source_data['name'],
            'source_type': 'rss',
            'category': category,
            'is_active': True,
        }
    )
    if created:
        print(f"✅ Добавлен источник: {source_data['name']}")
    else:
        print(f"ℹ Источник уже существует: {source_data['name']}")

print("\n🎉 Все источники добавлены!")