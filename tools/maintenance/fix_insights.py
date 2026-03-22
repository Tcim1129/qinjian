with open("backend/app/api/v1/insights.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the invalid Optional type annotation
content = content.replace("Optional[tuple[str], Optional[str]]", "Optional[tuple[str, Optional[str]]]")

with open("backend/app/api/v1/insights.py", "w", encoding="utf-8") as f:
    f.write(content)
