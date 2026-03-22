import os
import shutil

# Just create an empty valid ICO file or a small PNG pretending to be ICO
icon_path = os.path.join("web", "favicon.ico")
if not os.path.exists(icon_path):
    with open(icon_path, "wb") as f:
        # A tiny valid 1x1 transparent ICO
        f.write(bytes.fromhex("000001000100010100000100180030000000160000002800000001000000020000000100180000000000000000000000000000000000000000000000000000000000ffffff0000000000"))
    print("favicon.ico created")
