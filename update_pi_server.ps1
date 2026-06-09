param(
    [string]$PiHost = "192.168.1.209",
    [string]$PiUser = "mozes"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerTarget = "${PiUser}@${PiHost}:~/SmartHomeProject/smart_home_project/server/"
$CommonTarget = "${PiUser}@${PiHost}:~/SmartHomeProject/smart_home_project/common/"

Write-Host "Copying updated server code to Raspberry Pi..."
scp -r "$ProjectRoot\smart_home_project\server\*.py" $ServerTarget

Write-Host "Copying updated common protocol code to Raspberry Pi..."
scp -r "$ProjectRoot\smart_home_project\common\*.py" $CommonTarget

Write-Host "Restarting smart-home-server service..."
ssh "${PiUser}@${PiHost}" "sudo systemctl restart smart-home-server && sudo systemctl status smart-home-server --no-pager"

Write-Host "Done."
