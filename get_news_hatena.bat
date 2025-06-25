@echo off
cd /d %~dp0

REM 引数を表示（確認用）
echo 引数1: %1
echo 引数2: %2

REM Python スクリプトに引数を渡す
python ./src/get_news_hatena.py %1 %2
