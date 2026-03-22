with open("backend/app/api/v1/insights.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix another typing error tuple inside Optional
content = content.replace("Optional[tuple[Checkin], Optional[Checkin]]", "Optional[tuple[Checkin, Optional[Checkin]]]")
content = content.replace("Optional[tuple[str], Optional[str]]", "Optional[tuple[str, Optional[str]]]")

with open("backend/app/api/v1/insights.py", "w", encoding="utf-8") as f:
    f.write(content)
