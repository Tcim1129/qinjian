import re
import secrets

with open(".env", "r", encoding="utf-8") as f:
    content = f.read()

# Generate a strong secret key
new_key = secrets.token_hex(32)

content = re.sub(
    r'SECRET_KEY=.*',
    f'SECRET_KEY={new_key}',
    content
)

if "SECRET_KEY" not in content:
    content += f"\nSECRET_KEY={new_key}\n"
    
if "DEBUG=True" not in content:
    content += "\nDEBUG=True\n"

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)
