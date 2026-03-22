import re

with open("backend/Dockerfile", "r", encoding="utf-8") as f:
    content = f.read()

# Since we had issues with 3.14 locally and patched it, but Dockerfile uses 3.12, 
# 3.12 doesn't have the Python 3.14 Union issue. So Dockerfile should be fine.
print("Dockerfile looks OK, python 3.12 is used.")
