' VBScript to convert Markdown to Word using Word COM automation
' Usage: cscript convert_md_to_word.vbs

Option Explicit

Dim objWord, objDoc, objSelection
Dim strMdFile, strDocxFile
Dim fso, file, content

strMdFile = "C:\Users\colour\Desktop\亲健\亲健商业计划书.md"
strDocxFile = "C:\Users\colour\Desktop\亲健\亲健商业计划书.docx"

' Read Markdown file
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(strMdFile) Then
    WScript.Echo "Error: File not found: " & strMdFile
    WScript.Quit 1
End If

Set file = fso.OpenTextFile(strMdFile, 1, False, -1) ' -1 = Unicode
content = file.ReadAll
file.Close

' Create Word application
Set objWord = CreateObject("Word.Application")
objWord.Visible = False

' Create new document
Set objDoc = objWord.Documents.Add()
Set objSelection = objWord.Selection

' Set page margins (in points, 72 points = 1 inch)
objDoc.PageSetup.LeftMargin = 72
objDoc.PageSetup.RightMargin = 72
objDoc.PageSetup.TopMargin = 72
objDoc.PageSetup.BottomMargin = 72

' Set default font
objSelection.Font.Name = "宋体"
objSelection.Font.Size = 12

' Process content line by line
Dim lines, line, i
lines = Split(content, vbCrLf)

For i = 0 To UBound(lines)
    line = lines(i)
    
    ' Check for headers
    If Left(line, 2) = "# " Then
        ' H1 - Chapter title
        objSelection.Font.Name = "黑体"
        objSelection.Font.Size = 18
        objSelection.Font.Bold = True
        objSelection.ParagraphFormat.Alignment = 1 ' Center
        objSelection.TypeText Mid(line, 3)
        objSelection.TypeParagraph()
        objSelection.ParagraphFormat.Alignment = 0 ' Left
        objSelection.Font.Bold = False
    ElseIf Left(line, 3) = "## " Then
        ' H2
        objSelection.Font.Name = "黑体"
        objSelection.Font.Size = 14
        objSelection.Font.Bold = True
        objSelection.TypeText Mid(line, 4)
        objSelection.TypeParagraph()
        objSelection.Font.Bold = False
    ElseIf Left(line, 4) = "### " Then
        ' H3
        objSelection.Font.Name = "黑体"
        objSelection.Font.Size = 12
        objSelection.Font.Bold = True
        objSelection.TypeText Mid(line, 5)
        objSelection.TypeParagraph()
        objSelection.Font.Bold = False
    ElseIf Left(line, 3) = "**" AND Right(line, 2) = "**" Then
        ' Bold text
        objSelection.Font.Name = "宋体"
        objSelection.Font.Size = 12
        objSelection.Font.Bold = True
        objSelection.TypeText Mid(line, 3, Len(line) - 4)
        objSelection.TypeParagraph()
        objSelection.Font.Bold = False
    ElseIf Left(line, 2) = "- " Then
        ' Bullet point
        objSelection.Font.Name = "宋体"
        objSelection.Font.Size = 12
        objSelection.TypeText "• " & Mid(line, 3)
        objSelection.TypeParagraph()
    ElseIf Trim(line) = "" Then
        ' Empty line
        objSelection.TypeParagraph()
    ElseIf Left(line, 1) = "|" Then
        ' Table row - skip in this simple version
        ' Just add text without table formatting
        If InStr(line, "---") = 0 AND InStr(line, "表") = 0 Then
            objSelection.Font.Name = "宋体"
            objSelection.Font.Size = 10
            objSelection.TypeText Replace(Replace(line, "|", " "), "  ", " ")
            objSelection.TypeParagraph()
        End If
    Else
        ' Regular text
        objSelection.Font.Name = "宋体"
        objSelection.Font.Size = 12
        objSelection.TypeText line
        objSelection.TypeParagraph()
    End If
Next

' Save as DOCX
objDoc.SaveAs strDocxFile, 16 ' 16 = wdFormatDocumentDefault (DOCX)
objDoc.Close
objWord.Quit

Set objDoc = Nothing
Set objWord = Nothing
Set fso = Nothing

WScript.Echo "Success! Converted to: " & strDocxFile
