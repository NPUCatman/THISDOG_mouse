#requires -Version 5.1
[CmdletBinding()]
param()

# 仅在用户主动运行时应用本目录内的光标；不复制文件，不要求管理员权限。
# 首次备份永久保留；重复应用失败时，回滚到本次应用之前的状态。
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
    if (($full -ne $themeRoot) -and -not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "路径超出主题目录：$full"
    }
    # 禁止目录联接、符号链接和其他重解析点将读写引向目录以外。
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
    if ($exists) {
        return [pscustomobject]@{ Name = $Name; Exists = $true; Kind = $Key.GetValueKind($Name).ToString(); Value = $Key.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
    }
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

function Assert-ValueState($Entry) {
    if ($Entry.Exists -isnot [bool]) { throw '备份中的存在标记无效。' }
    if ($Entry.Exists) {
        $kind = [Microsoft.Win32.RegistryValueKind][Enum]::Parse([Microsoft.Win32.RegistryValueKind], [string]$Entry.Kind)
        if ($kind -eq [Microsoft.Win32.RegistryValueKind]::Unknown) { throw '备份包含不支持的注册表类型。' }
        if ($null -eq $Entry.Value) { throw '备份中的注册表值为空。' }
    }
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
    # 使用内存中的 P/Invoke 类型，避免 Add-Type 编译时生成目录外临时文件。
    if ($null -eq ('ZheGouCursorNative' -as [type])) {
        $assemblyName = New-Object Reflection.AssemblyName('ZheGouCursorNativeAssembly')
        if ([AppDomain].GetMethod('DefineDynamicAssembly', [type[]]@([Reflection.AssemblyName], [Reflection.Emit.AssemblyBuilderAccess]))) {
            $assembly = [AppDomain]::CurrentDomain.DefineDynamicAssembly($assemblyName, [Reflection.Emit.AssemblyBuilderAccess]::Run)
        } else {
            $assembly = [Reflection.Emit.AssemblyBuilder]::DefineDynamicAssembly($assemblyName, [Reflection.Emit.AssemblyBuilderAccess]::Run)
        }
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
    $manifestPath = Assert-ThemePath (Join-Path $themeRoot 'theme.json') -File
    $theme = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (($theme.name -ne $themeName) -or ($null -eq $theme.mapping) -or ($theme.mapping -isnot [pscustomobject])) { throw 'theme.json 需要 name="这狗" 和 mapping 对象。' }
    if ($themeRoot.Contains(',')) { throw '主题目录不能含逗号，Windows 方案使用逗号分隔文件名。' }
    $paths = @{}
    foreach ($property in $theme.mapping.PSObject.Properties) {
        if ($roles -cnotcontains $property.Name) { throw "未知的 Windows 光标角色：$($property.Name)" }
        if (($property.Value -isnot [string]) -or [string]::IsNullOrWhiteSpace($property.Value)) { throw 'mapping 的文件路径必须是非空字符串。' }
        $relative = [string]$property.Value
        if ([IO.Path]::IsPathRooted($relative) -or $relative.Contains(':')) { throw "mapping 只接受主题目录内的相对路径：$relative" }
        $full = Assert-ThemePath (Join-Path $themeRoot $relative) -File
        if (@('.cur', '.ani') -notcontains [IO.Path]::GetExtension($full).ToLowerInvariant()) { throw "光标文件扩展名必须为 .cur 或 .ani：$relative" }
        if ($full.Contains(',')) { throw "光标路径不能含逗号：$relative" }
        $paths[$property.Name] = $full
    }
    foreach ($required in $roles[0..14]) { if (-not $paths.ContainsKey($required)) { throw "theme.json 缺少必需角色：$required" } }

    $backupDir = Assert-ThemePath (Join-Path $themeRoot 'backup')
    if (-not (Test-Path -LiteralPath $backupDir)) { $null = New-Item -ItemType Directory -Path $backupDir }
    if (-not (Test-Path -LiteralPath $backupDir -PathType Container)) { throw 'backup 不是目录。' }
    $lockPath = Assert-ThemePath (Join-Path $backupDir 'cursor_settings.lock')
    try { $lock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) }
    catch { throw '另一个应用或恢复脚本正在运行，或无法写入主题备份目录。' }
    $before = Get-CursorState
    $backupPath = Assert-ThemePath (Join-Path $backupDir 'current_cursors.clixml')
    if (Test-Path -LiteralPath $backupPath) {
        Assert-Snapshot (Import-Clixml -LiteralPath (Assert-ThemePath $backupPath -File))
    } else {
        $temporary = Assert-ThemePath (Join-Path $backupDir ('.current_cursors.' + [Guid]::NewGuid().ToString('N') + '.tmp'))
        try {
            $before | Export-Clixml -LiteralPath $temporary -Depth 12 -Encoding UTF8 -NoClobber
            Assert-Snapshot (Import-Clixml -LiteralPath $temporary)
            [IO.File]::Move($temporary, $backupPath)
        } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force } }
    }

    try {
        $key = $null; $schemes = $null
        try {
            $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($cursorKeyPath)
            foreach ($role in $roles) { if ($paths.ContainsKey($role)) { $key.SetValue($role, $paths[$role], [Microsoft.Win32.RegistryValueKind]::ExpandString) } }
            $key.SetValue('', $themeName, [Microsoft.Win32.RegistryValueKind]::String)
            $key.SetValue('Scheme Source', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
            $parts = @(foreach ($role in $roles) {
                if ($paths.ContainsKey($role)) { $paths[$role] }
                else { [string]$key.GetValue($role, '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
            })
            $schemes = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($schemeKeyPath)
            $schemes.SetValue($themeName, ($parts -join ','), [Microsoft.Win32.RegistryValueKind]::String)
        } finally {
            if ($null -ne $schemes) { $schemes.Dispose() }
            if ($null -ne $key) { $key.Dispose() }
        }
        Update-WindowsCursors
    } catch {
        $applyError = $_
        try { Set-CursorState $before; Update-WindowsCursors }
        catch { throw "应用失败，而且自动回滚未完全成功。应用错误：$applyError；回滚错误：$_。请保留 backup 并运行恢复脚本。" }
        throw "应用失败，已自动恢复本次操作前的状态。原因：$applyError"
    }
    Write-Host "已应用“$themeName”光标。请保留主题文件夹，Windows 直接引用此处文件。"
    Write-Host "首次备份：$backupPath"
    Write-Host "恢复方式：手动运行 tools\restore_theme.ps1。"
} finally {
    if ($null -ne $lock) { $lock.Dispose() }
}
