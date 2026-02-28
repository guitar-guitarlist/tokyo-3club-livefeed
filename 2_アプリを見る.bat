@echo off
title ライブスケジュール アプリ起動
echo アプリを準備しています...
echo ブラウザが自動的に開きます。
echo.
echo ※ アプリの使用が終わったら、この黒い画面は右上の[X]ボタンで閉じてください。
echo ========================================================
start http://localhost:8080
python -m http.server 8080
