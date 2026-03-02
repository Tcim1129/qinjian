# 亲健自动部署脚本
# 服务器: 143.198.110.145
# 执行时间: $(Get-Date)

$server = "143.198.110.145"
$username = "root"
$password = "7507906119HJL"

# 部署命令
$commands = @"
cd /opt/qinjian
echo '[1/5] 拉取最新代码...'
git pull origin main
echo ''
echo '[2/5] 停止现有服务...'
docker-compose down 2>/dev/null || true
echo ''
echo '[3/5] 构建并启动服务...'
docker-compose up -d --build
echo ''
echo '[4/5] 等待服务启动...'
sleep 15
echo ''
echo '[5/5] 检查服务状态...'
docker-compose ps
echo ''
echo '后端日志:'
docker-compose logs --tail=30 backend 2>/dev/null || echo '暂无日志'
echo ''
echo '✅ 部署完成！'
echo '访问: http://143.198.110.145:8080'
"@

# 使用 sshpass 或 expect 来自动输入密码
# 由于Windows环境，这里提供手动执行命令

Write-Host "请在PowerShell中执行以下命令：" -ForegroundColor Green
Write-Host ""
Write-Host "ssh $username@$server" -ForegroundColor Yellow
Write-Host ""
Write-Host "然后输入密码: $password" -ForegroundColor Yellow
Write-Host ""
Write-Host "连接后执行以下命令：" -ForegroundColor Cyan
Write-Host $commands -ForegroundColor White
