import re

with open("backend/app/core/config.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update config to read from env or use wildcard
content = re.sub(
    r'FRONTEND_ORIGIN: str = "http://localhost:3000"',
    r'FRONTEND_ORIGIN: str = "http://localhost:3000"', # Keeping it as is, but we will modify main.py to allow all for dev
    content
)

with open("backend/app/core/config.py", "w", encoding="utf-8") as f:
    f.write(content)

with open("backend/app/main.py", "r", encoding="utf-8") as f:
    main_content = f.read()

# Make CORS more permissive for easier deployment testing
main_content = re.sub(
    r'allow_origins=\[settings\.FRONTEND_ORIGIN\],',
    r'allow_origins=["*"],',
    main_content
)

with open("backend/app/main.py", "w", encoding="utf-8") as f:
    f.write(main_content)

