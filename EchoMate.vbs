Option Explicit
' Windowless entry point. Paths and working directory are resolved at runtime.
Dim fs, sh, root, python, env, entry
Set fs = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fs.GetParentFolderName(WScript.ScriptFullName)
python = fs.BuildPath(root, ".venv-gemma4\Scripts\pythonw.exe")
If Not fs.FileExists(python) Then
    If Not WScript.Arguments.Named.Exists("check") Then
        MsgBox "EchoMate Python environment was not found. Check the setup guide.", 16, "EchoMate"
    End If
    WScript.Quit 1
End If
If WScript.Arguments.Named.Exists("check") Then WScript.Quit 0
sh.CurrentDirectory = root
Set env = sh.Environment("Process")
env("PYTHONPATH") = fs.BuildPath(root, "src")
env("HF_HUB_OFFLINE") = "1"
env("TRANSFORMERS_OFFLINE") = "1"
entry = "echomate_bot.lime_desktop"
If WScript.Arguments.Named.Exists("legacy") Then entry = "echomate_bot.desktop"
sh.Run Chr(34) & python & Chr(34) & " -m " & entry, 0, False
