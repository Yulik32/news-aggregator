@echo off
cd /d D:\Whether\news_aggregator
D:\Whether\news_aggregator\venv\Scripts\python.exe D:\Whether\news_aggregator\manage.py parse_rss --all --proxy "http://userappl:bynthytn@vbflxproxyap:93" >> D:\Whether\news_aggregator\logs\parser.log 2>&1