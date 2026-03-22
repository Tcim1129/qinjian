import re

with open("web/js/ws.js", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("QJ_CONFIG.apiBaseUrl", "QJ_CONFIG.apiRoot")

with open("web/js/ws.js", "w", encoding="utf-8") as f:
    f.write(content)

