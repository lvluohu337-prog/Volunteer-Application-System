@echo off
setlocal
set "PROJECT_ROOT=D:\2026workspace\Volunteer Application System"
set "PG_ROOT=%PROJECT_ROOT%\.local\postgresql"
set "POSTGRES_EXE=%PG_ROOT%\16\bin\postgres.exe"
set "DATA_DIR=%PG_ROOT%\16\data"
set "STDOUT_LOG=%PG_ROOT%\postgres-stdout.log"
set "STDERR_LOG=%PG_ROOT%\postgres-stderr.log"
set "LISTEN_ADDRESSES=127.0.0.1,192.168.66.102"

"%POSTGRES_EXE%" -D "%DATA_DIR%" -h "%LISTEN_ADDRESSES%" -p 5432 -c default_text_search_config=pg_catalog.simple 1>>"%STDOUT_LOG%" 2>>"%STDERR_LOG%"
