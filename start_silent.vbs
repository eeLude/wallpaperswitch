Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir
mainScript = """" & currentDir & "\main.py"""

pythonw = "pythonw.exe"
If fso.FileExists("C:\Python314\pythonw.exe") Then
    pythonw = """C:\Python314\pythonw.exe"""
ElseIf fso.FileExists("C:\Program Files\Python314\pythonw.exe") Then
    pythonw = """C:\Program Files\Python314\pythonw.exe"""
End If

WshShell.Run pythonw & " " & mainScript, 0, False

Set WshShell = Nothing
Set fso = Nothing
