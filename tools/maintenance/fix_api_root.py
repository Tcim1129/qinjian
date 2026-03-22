import re

with open("web/js/api.js", "r", encoding="utf-8") as f:
    content = f.read()

# Make sure it listens to QJ_CONFIG if present, so we can override via config.local.js
# But since we are on localhost, it will fallback to http://localhost:8000/api/v1 which is correct for local testing

content = re.sub(
    r'const API_ROOT = \(\(\) => \{',
    r'const API_ROOT = window.QJ_CONFIG?.apiRoot || (() => {',
    content
)

with open("web/js/api.js", "w", encoding="utf-8") as f:
    f.write(content)

