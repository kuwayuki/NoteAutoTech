@echo off
cd /d %~dp0

REM ������\���i�m�F�p�j
echo ����1: %1
echo ����2: %2

REM Python �X�N���v�g�Ɉ�����n��
python ./src/get_news_hatena.py %1 %2
