@echo off
chcp 65001 >nul
echo ==========================================
echo  亲健 - 本地测试启动脚本
echo ==========================================
echo.

REM 检查 Docker 是否安装
docker --version > nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未安装，请先安装 Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 检查 .env 文件是否存在
if not exist "backend\.env" (
    echo [提示] 未找到 backend\.env 文件，正在创建...
    copy "backend\.env.example" "backend\.env"
    echo.
    echo ⚠️  重要: 请编辑 backend\.env 文件，填入你的 SILICONFLOW_API_KEY
    echo    获取地址: https://siliconflow.cn
    echo.
    notepad "backend\.env"
    echo.
    echo 请保存文件后按任意键继续...
    pause > nul
)

echo [1/4] 停止旧容器...
docker-compose down > nul 2>&1

echo [2/4] 拉取最新镜像...
docker-compose pull > nul 2>&1

echo [3/4] 构建并启动服务...
docker-compose up -d --build

if errorlevel 1 (
    echo.
    echo [错误] 启动失败，请检查 Docker 是否正常运行
    pause
    exit /b 1
)

echo [4/4] 等待服务就绪...
timeout /t 5 /nobreak > nul

echo.
echo ==========================================
echo  ✅ 启动成功！
echo ==========================================
echo.
echo  访问地址: http://localhost:8080
echo.
echo  常用命令:
echo    - 查看日志: docker-compose logs -f
echo    - 停止服务: docker-compose down
echo    - 重启服务: docker-compose restart
echo.
echo  按任意键打开浏览器...
pause > nul
start http://localhost:8080
