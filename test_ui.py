"""
UI 截图测试脚本 — 亲健前端所有页面
使用 file:// 协议直接打开 index.html，无需后端
"""

import os, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent
HTML = ROOT / "web" / "index.html"
SHOTS = ROOT / "screenshots"
SHOTS.mkdir(exist_ok=True)

FILE_URL = HTML.as_uri()

# 所有需要截图的页面 ID（showPage 参数）
PAGES = [
    "home",
    "checkin",
    "discover",
    "longdistance",
    "attachment-test",
    "health-test",
    "community",
    "challenges",
    "courses",
    "experts",
    "membership",
    "report",
    "profile",
]

console_errors = []


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 390, "height": 844}
        )  # iPhone 14 尺寸

        # 收集控制台错误
        page.on(
            "console",
            lambda msg: (
                console_errors.append(f"[{msg.type}] {msg.text}")
                if msg.type in ("error", "warning")
                else None
            ),
        )
        page.on("pageerror", lambda err: console_errors.append(f"[PAGE_ERROR] {err}"))

        # 加载页面
        page.goto(FILE_URL)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)

        for pid in PAGES:
            # 切换页面
            page.evaluate(f"showPage('{pid}')")
            page.wait_for_timeout(300)

            # 截图
            fname = f"{pid}.png"
            page.screenshot(path=str(SHOTS / fname), full_page=True)
            print(f"  [OK] {pid} -> screenshots/{fname}")

        # 测试 Discover → 子页面导航
        page.evaluate("showPage('discover')")
        page.wait_for_timeout(200)
        # 点击第一个 discover-item
        items = page.locator(".discover-item").all()
        print(f"\n  Discover grid items: {len(items)}")
        for i, item in enumerate(items):
            title = item.locator(".discover-item__title").text_content()
            print(f"    [{i}] {title}")

        # 测试健康测试页交互
        page.evaluate("showPage('health-test')")
        page.wait_for_timeout(200)
        page.screenshot(path=str(SHOTS / "health-test-start.png"), full_page=True)

        # 点击第一个选项试试
        try:
            page.evaluate("initHealthTest()")
            page.wait_for_timeout(200)
            page.screenshot(path=str(SHOTS / "health-test-q1.png"), full_page=True)
            # 回答所有 10 道题（选第 3 个选项，值=4）
            for q in range(10):
                page.evaluate("answerHealthQuestion(4)")
                page.wait_for_timeout(150)
            page.screenshot(path=str(SHOTS / "health-test-result.png"), full_page=True)
            print("  [OK] Health test 全流程完成")
        except Exception as e:
            print(f"  [WARN] Health test 交互失败: {e}")

        # 输出控制台错误
        print(f"\n{'=' * 50}")
        print(f"控制台错误/警告: {len(console_errors)} 条")
        for err in console_errors[:30]:
            print(f"  {err}")
        if len(console_errors) > 30:
            print(f"  ... 还有 {len(console_errors) - 30} 条")

        browser.close()


if __name__ == "__main__":
    main()
