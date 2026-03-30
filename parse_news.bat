@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo ========================================
echo    ЗАПУСК ПАРСИНГА НОВОСТЕЙ
echo ========================================
echo.

:: Создаем папку для логов если её нет
if not exist "D:\New\news_aggregator\logs" mkdir D:\New\news_aggregator\logs

:: Записываем время запуска
echo [%date% %time%] Запуск парсинга... >> D:\New\news_aggregator\logs\parser.log

:: Переходим в папку проекта
cd /d D:\New\news_aggregator
echo Перешли в папку: %cd% >> D:\New\news_aggregator\logs\parser.log

:: Проверяем существование python
if not exist D:\New\venv\Scripts\python.exe (
    echo [ОШИБКА] Python не найден в D:\New\venv\Scripts\python.exe
    echo [ОШИБКА] Python не найден >> D:\New\news_aggregator\logs\parser.log
    pause
    exit /b 1
)

:: Запускаем парсинг напрямую
echo Запуск парсинга...
echo Запуск команды: python manage.py parse_rss --all --proxy "http://userappl:bynthytn@vbflxproxyap:93" >> D:\New\news_aggregator\logs\parser.log

D:\New\venv\Scripts\python.exe manage.py parse_rss --all --proxy "http://userappl:bynthytn@vbflxproxyap:93" >> D:\New\news_aggregator\logs\parser.log 2>&1

:: Проверяем результат
if %errorlevel% equ 0 (
    echo [%date% %time%] Парсинг выполнен успешно!
    echo [%date% %time%] Парсинг выполнен успешно >> D:\New\news_aggregator\logs\parser.log
) else (
    echo [%date% %time%] Ошибка при парсинге! Код ошибки: %errorlevel%
    echo [%date% %time%] Ошибка при парсинге! Код ошибки: %errorlevel% >> D:\New\news_aggregator\logs\parser.log
)

echo.
echo ========================================
echo    ГОТОВО! Смотри лог в папке logs
echo ========================================
echo.

:: Показываем последние 20 строк лога
echo Последние записи в логе:
echo ------------------------
powershell -Command "Get-Content D:\New\news_aggregator\logs\parser.log -Tail 20 -Encoding UTF8"

pause