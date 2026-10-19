Option Explicit
' User-invoked offline check; never uses the operating credential directory.
Dim fs, sh, home, python, env
Set fs=CreateObject("Scripting.FileSystemObject")
Set sh=CreateObject("WScript.Shell")
home=fs.GetParentFolderName(WScript.ScriptFullName)
python=fs.BuildPath(home,"runtime\pythonw.exe")
If Not fs.FileExists(python) Then python=fs.BuildPath(home,".venv-gemma4\Scripts\pythonw.exe")
If Not fs.FileExists(python) Then WScript.Quit 1
If WScript.Arguments.Named.Exists("check") Then WScript.Quit 0
sh.CurrentDirectory=home
Set env=sh.Environment("Process")
env("PYTHONPATH")=fs.BuildPath(home,"src")
If fs.FileExists(fs.BuildPath(home,"runtime\pythonw.exe")) Then env("PYTHONHOME")=fs.BuildPath(home,"runtime")
sh.Run Chr(34) & python & Chr(34) & " -m echomate_bot.user_check", 0, False
