# wb_discover_endpoints.py
from playwright.sync_api import sync_playwright
from urllib.parse import quote_plus, urlsplit
import sys
import json
from collections import Counter


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "кроссовки"
    unique_endpoints = set()   # netloc + path без query
    hit_counter = Counter()    # сколько раз встретился точный URL (с query)
    saved = False
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        def on_response(resp):
            nonlocal saved
            if (saved):
                return
            # фильтруем по content-type
            ctype = (resp.headers.get("content-type") or "").lower()
            if "application/json" not in ctype:
                return

            url = resp.url
            parts = urlsplit(url)
            # ловим только домены Wildberries
            if not parts.netloc.endswith("wb.ru"):
                return
            if "cards/v4/list" in parts.path:
                try:
                    data = resp.json()
                except Exception as e:
                    return
                with open("cards_sample.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print("Сохранён пример ответа {url} в cards_sample.json")
                saved = True
            # ключ для «семейства» эндпоинта: хост + путь (без query)
            family = f"{parts.netloc}{parts.path}"
            unique_endpoints.add(family)

            # считаем точные урлы (с query), чтобы видеть самые «шумные»
            hit_counter[url] += 1

        page.on("response", on_response)
        page.goto(
            "https://www.wildberries.ru/catalog/0/search.aspx?search=" +
            quote_plus(query),
            timeout=60_000,
        )

        # даём странице подгрузиться и проскроллим, чтобы вытянуть больше запросов
        page.wait_for_timeout(4000)
        for _ in range(8):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(800)

        # выводим результат
        print("\n=== УНИКАЛЬНЫЕ ЭНДПОИНТЫ (host + path) ===")
        for ep in sorted(unique_endpoints):
            print(ep)

        # сохраним в файл, чтобы не потерять
        with open("wb_endpoints.txt", "w", encoding="utf-8") as f:
            for ep in sorted(unique_endpoints):
                f.write(ep + "\n")

        # покажем топ-URL по количеству срабатываний (с query)
        print("\n=== ТОП ТОЧНЫХ URL (с query) ===")
        for url, n in hit_counter.most_common(15):
            print(n, url)

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
