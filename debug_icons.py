"""诊断 SVG 图标渲染问题"""

from playwright.sync_api import sync_playwright
import pathlib

HTML = pathlib.Path(r"C:\Users\colour\Desktop\亲健\web\index.html").as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(HTML)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(500)

    # 检查 .icon 元素的实际 computed styles
    info = page.evaluate("""() => {
        const icons = document.querySelectorAll('svg.icon');
        const results = [];
        for (let i = 0; i < Math.min(icons.length, 5); i++) {
            const el = icons[i];
            const cs = getComputedStyle(el);
            const bbox = el.getBoundingClientRect();
            results.push({
                index: i,
                outerHTML: el.outerHTML.slice(0, 200),
                computedWidth: cs.width,
                computedHeight: cs.height,
                fill: cs.fill,
                stroke: cs.stroke,
                strokeWidth: cs.strokeWidth,
                display: cs.display,
                bboxWidth: bbox.width,
                bboxHeight: bbox.height,
                parentTag: el.parentElement?.tagName,
                parentClass: el.parentElement?.className,
            });
        }
        return results;
    }""")

    for item in info:
        print(f"--- Icon #{item['index']} ---")
        for k, v in item.items():
            print(f"  {k}: {v}")
        print()

    # 也检查隐藏的 SVG sprite 容器
    sprite_info = page.evaluate("""() => {
        const hidden = document.querySelector('div[hidden]');
        if (!hidden) return 'No hidden div found';
        const svg = hidden.querySelector('svg');
        if (!svg) return 'No SVG in hidden div';
        const symbols = svg.querySelectorAll('symbol');
        return {
            hiddenDisplay: getComputedStyle(hidden).display,
            svgDisplay: getComputedStyle(svg).display,
            symbolCount: symbols.length,
            firstSymbol: symbols[0]?.id,
            svgBBox: svg.getBoundingClientRect(),
            // 检查 hidden div 是否真的隐藏
            hiddenBBox: hidden.getBoundingClientRect(),
        };
    }""")
    print("--- SVG Sprite Container ---")
    print(sprite_info)

    # 检查是否有内联 style 或其他覆盖
    override_check = page.evaluate("""() => {
        const icon = document.querySelector('svg.icon');
        if (!icon) return 'No icon found';
        return {
            inlineStyle: icon.getAttribute('style'),
            classNames: icon.className.baseVal || icon.className,
            viewBox: icon.getAttribute('viewBox'),
            width: icon.getAttribute('width'),
            height: icon.getAttribute('height'),
        };
    }""")
    print("\n--- Override Check ---")
    print(override_check)

    # 截图 checkin 页 — 看看是不是所有页面都有这个问题
    page.evaluate("showPage('checkin')")
    page.wait_for_timeout(300)
    page.screenshot(path=r"C:\Users\colour\Desktop\亲健\screenshots\debug-checkin.png")

    # 截图 discover 页
    page.evaluate("showPage('discover')")
    page.wait_for_timeout(300)
    page.screenshot(path=r"C:\Users\colour\Desktop\亲健\screenshots\debug-discover.png")

    print("\nScreenshots saved.")
    browser.close()
