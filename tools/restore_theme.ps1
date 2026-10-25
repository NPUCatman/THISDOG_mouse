#requires -Version 5.1
[CmdletBinding()]
param()

# 恢复首次应用之前的光标值、默认方案名以及原来的同名方案。
# 不依赖 theme.json 或光标文件，备份保留在本主题目录内。
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$themeRoot = [IO.Path]::GetFullPath(([IO.Path]::GetDirectoryName($PSScriptRoot)))
$themeName = '这狗'
$cursorKeyPath = 'Control Panel\Cursors'
$schemeKeyPath = 'Control Panel\Cursors\Schemes'
$roles = @('Arrow', 'Help', 'AppStarting', 'Wait', 'Crosshair', 'IBeam', 'NWPen', 'No', 'SizeNS', 'SizeWE', 'SizeNWSE', 'SizeNESW', 'SizeAll', 'UpArrow', 'Hand', 'Pin', 'Person')
$valueNames = @('') + $roles + @('Scheme Source')

function Assert-ThemePath([string]$Path, [switch]$File) {
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = $themeRoot.TrimEnd('\') + '\'
    if (($full -ne $themeRoot) -and -not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "路径超出主题目录：$full" }
    $part = $full
    while ($part -and ($part.Length -ge $themeRoot.Length)) {
        if (Test-Path -LiteralPath $part) {
            $item = Get-Item -LiteralPath $part -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "不支持重解析点：$part" }
        }
        if ($part -eq $themeRoot) { break }
        $part = [IO.Path]::GetDirectoryName($part)
    }
    if ($File -and -not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "文件不存在：$full" }
    return $full
}

function Read-ValueState($Key, [string]$Name) {
    $exists = ($null -ne $Key) -and (@($Key.GetValueNames()) -contains $Name)
    if ($exists) { return [pscustomobject]@{ Name = $Name; Exists = $true; Kind = $Key.GetValueKind($Name).ToString(); Value = $Key.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) } }
    return [pscustomobject]@{ Name = $Name; Exists = $false; Kind = $null; Value = $null }
}

function Get-CursorState {
    $key = $null; $schemes = $null
    try {
        $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($cursorKeyPath)
        $schemes = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($schemeKeyPath)
        $values = @(foreach ($name in $valueNames) { Read-ValueState $key $name })
        return [pscustomobject]@{
            SchemaVersion = 1; ThemeName = $themeName; SavedAt = [DateTime]::Now.ToString('o')
            CursorKeyExisted = ($null -ne $key); SchemesKeyExisted = ($null -ne $schemes)
            CursorValues = $values; SchemeValue = (Read-ValueState $schemes $themeName)
        }
    } finally {
        if ($null -ne $schemes) { $schemes.Dispose() }
        if ($null -ne $key) { $key.Dispose() }
    }
}

function Assert-ValueState($Entry) {
    if ($Entry.Exists -isnot [bool]) { throw '备份中的存在标记无效。' }
    if ($Entry.Exists) {
        $kind = [Microsoft.Win32.RegistryValueKind][Enum]::Parse([Microsoft.Win32.RegistryValueKind], [string]$Entry.Kind)
        if ($kind -eq [Microsoft.Win32.RegistryValueKind]::Unknown) { throw '备份包含不支持的注册表类型。' }
        if ($null -eq $Entry.Value) { throw '备份中的注册表值为空。' }
    }
}

function Assert-Snapshot($State) {
    if (($State.SchemaVersion -ne 1) -or ($State.ThemeName -ne $themeName)) { throw '备份版本或主题名称不匹配。' }
    if (($State.CursorKeyExisted -isnot [bool]) -or ($State.SchemesKeyExisted -isnot [bool])) { throw '备份中的注册表键状态无效。' }
    $seen = @{}
    foreach ($entry in @($State.CursorValues)) {
        if (($valueNames -cnotcontains [string]$entry.Name) -or $seen.ContainsKey([string]$entry.Name)) { throw '备份包含未知或重复的光标值。' }
        $seen[[string]$entry.Name] = $true
        Assert-ValueState $entry
    }
    if ($seen.Count -ne $valueNames.Count) { throw '备份中的光标值不完整。' }
    if ($State.SchemeValue.Name -cne $themeName) { throw '备份中的方案名无效。' }
    Assert-ValueState $State.SchemeValue
}

function Set-ValueState($Key, $Entry) {
    if ($Entry.Exists) {
        $kind = [Microsoft.Win32.RegistryValueKind][Enum]::Parse([Microsoft.Win32.RegistryValueKind], [string]$Entry.Kind)
        $value = $Entry.Value
        if ($kind -eq [Microsoft.Win32.RegistryValueKind]::DWord) { $value = [int]$value }
        elseif ($kind -eq [Microsoft.Win32.RegistryValueKind]::QWord) { $value = [long]$value }
        elseif ($kind -eq [Microsoft.Win32.RegistryValueKind]::Binary -or $kind -eq [Microsoft.Win32.RegistryValueKind]::None) { $value = [byte[]]$value }
        elseif ($kind -eq [Microsoft.Win32.RegistryValueKind]::MultiString) { $value = [string[]]$value }
        else { $value = [string]$value }
        $Key.SetValue([string]$Entry.Name, $value, $kind)
    } else { $Key.DeleteValue([string]$Entry.Name, $false) }
}

function Remove-EmptyKey([string]$Path) {
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($Path)
    $empty = $false
    try { if ($null -ne $key) { $empty = ($key.ValueCount -eq 0 -and $key.SubKeyCount -eq 0) } }
    finally { if ($null -ne $key) { $key.Dispose() } }
    if ($empty) { [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKey($Path, $false) }
}

function Set-CursorState($State) {
    Assert-Snapshot $State
    $key = $null; $schemes = $null
    try {
        $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($cursorKeyPath)
        foreach ($entry in @($State.CursorValues)) { Set-ValueState $key $entry }
        $schemes = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($schemeKeyPath)
        Set-ValueState $schemes $State.SchemeValue
    } finally {
        if ($null -ne $schemes) { $schemes.Dispose() }
        if ($null -ne $key) { $key.Dispose() }
    }
    if (-not $State.SchemesKeyExisted) { Remove-EmptyKey $schemeKeyPath }
    if (-not $State.CursorKeyExisted) { Remove-EmptyKey $cursorKeyPath }
}

function Update-WindowsCursors {
    # 仅生成内存类型，不使用会创建临时编译文件的 Add-Type。
    if ($null -eq ('ZheGouCursorNative' -as [type])) {
        $assemblyName = New-Object Reflection.AssemblyName('ZheGouCursorNativeAssembly')
        if ([AppDomain].GetMethod('DefineDynamicAssembly', [type[]]@([Reflection.AssemblyName], [Reflection.Emit.AssemblyBuilderAccess]))) {
            $assembly = [AppDomain]::CurrentDomain.DefineDynamicAssembly($assemblyName, [Reflection.Emit.AssemblyBuilderAccess]::Run)
        } else { $assembly = [Reflection.Emit.AssemblyBuilder]::DefineDynamicAssembly($assemblyName, [Reflection.Emit.AssemblyBuilderAccess]::Run) }
        $module = $assembly.DefineDynamicModule('ZheGouCursorNativeModule')
        $builder = $module.DefineType('ZheGouCursorNative', [Reflection.TypeAttributes]'Public, Sealed, Abstract')
        $method = $builder.DefinePInvokeMethod('SystemParametersInfo', 'user32.dll', [Reflection.MethodAttributes]'Public, Static, PinvokeImpl', [Reflection.CallingConventions]::Standard, [int], [type[]]@([uint32], [uint32], [IntPtr], [uint32]), [Runtime.InteropServices.CallingConvention]::Winapi, [Runtime.InteropServices.CharSet]::Auto)
        $method.SetImplementationFlags($method.GetMethodImplementationFlags() -bor [Reflection.MethodImplAttributes]::PreserveSig)
        $null = $builder.CreateType()
    }
    $native = 'ZheGouCursorNative' -as [type]
    $result = $native.GetMethod('SystemParametersInfo').Invoke($null, [object[]]@([uint32]0x0057, [uint32]0, [IntPtr]::Zero, [uint32]0))
    if ($result -eq 0) { throw 'Windows 刷新光标失败。' }
}

$lock = $null
try {
    $null = Assert-ThemePath $themeRoot
    $backupDir = Assert-ThemePath (Join-Path $themeRoot 'backup')
    $backupPath = Assert-ThemePath (Join-Path $backupDir 'current_cursors.clixml') -File
    $lockPath = Assert-ThemePath (Join-Path $backupDir 'cursor_settings.lock')
    try { $lock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) }
    catch { throw '另一个应用或恢复脚本正在运行，或无法写入主题备份目录。' }
    $saved = Import-Clixml -LiteralPath $backupPath
    Assert-Snapshot $saved
    $before = Get-CursorState
    try { Set-CursorState $saved; Update-WindowsCursors }
    catch {
        $restoreError = $_
        try { Set-CursorState $before; Update-WindowsCursors }
        catch { throw "恢复失败，而且自动回滚未完全成功。恢复错误：$restoreError；回滚错误：$_。首次备份仍保留在 $backupPath。" }
        throw "恢复失败，已自动回滚到本次恢复操作前的状态。原因：$restoreError"
    }
    Write-Host '已恢复首次应用之前的光标和方案设置。'
    Write-Host "首次备份已保留：$backupPath"
} finally {
    if ($null -ne $lock) { $lock.Dispose() }
}
