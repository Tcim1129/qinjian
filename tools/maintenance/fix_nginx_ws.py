with open("nginx.conf", "r", encoding="utf-8") as f:
    content = f.read()

replacement = """    # API 反向代理 (含 WebSocket 支持)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }"""

if "proxy_set_header Upgrade" not in content:
    content = content.replace(
        "    # API 反向代理\n    location /api/ {\n        proxy_pass http://backend:8000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_read_timeout 120s;\n        proxy_send_timeout 120s;\n    }",
        replacement
    )
    with open("nginx.conf", "w", encoding="utf-8") as f:
        f.write(content)
