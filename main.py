from playwright.sync_api import sync_playwright
from urllib.parse import quote_plus, urlsplit
# удобно собирать списки/множества по ключам
from collections import defaultdict
from db_sqlalchemy import init_db, upsert_products
import pandas as pd
import sys
import time
import argparse


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument("query", nargs="?", default="кроссовки",
                   help="поисковая фраза")
    p.add_argument("--max", type=int, default=40,
                   help="сколько карточек собрать")
    p.add_argument("--headless", action="store_true",
                   help="запуск без окна браузера")
    p.add_argument("--delay", type=int, default=600,
                   help="пауза между скроллами (мс)")
    return p.parse_args()


def main():
    args = parse_args()
    query = args.query
    stop_collecting = False
    if (len(query) > 1):
        last_added_at = time.time()
        max_items = args.max
        delay_ms = args.delay
        seen_ids = set()  # для уникальности
        rows = []
        with sync_playwright() as pw:
            # окно видно, удобно дебажить
            browser = pw.chromium.launch(headless=args.headless)
            context = browser.new_context()
            page = context.new_page()

            def on_response(resp):
                nonlocal stop_collecting
                nonlocal last_added_at
                nonlocal rows
                if stop_collecting:
                    return
                ctype = (resp.headers.get("content-type") or "").lower()
                # Фильтруем потенциальные API-эндпоинты WB, которые возвращают JSON
                if "application/json" not in ctype:
                    return
                parts = urlsplit(resp.url)
                if not parts.netloc.endswith("wb.ru"):
                    return

                if "cards/v4/list" not in parts.path:
                    return

                try:
                    data = resp.json()
                except Exception as e:
                    print(f"Error parsing JSON: {e}")
                    return
                products = (
                    data.get('products')
                    if isinstance(data, dict) else None
                )
                if not products:
                    return
                nonlocal last_added_at  # отметим момент, когда реально прилетели новые карточки
                added = 0
                for item in products:
                    try:
                        pid = item.get("id")
                        if not pid or pid in seen_ids:
                            continue
                        seen_ids.add(pid)
                        name = item.get("name", "")
                        brand = item.get("brand", "")
                        rating = item.get("reviewRating", 0)
                        feedbacks = item.get("feedbacks", 0)
                        conditions = set()
                        price = None
                        conditions_list = (
                            item.get("sizes")
                            if isinstance(item, dict) else None
                        )
                        if conditions_list is not None:
                            conditions.add("size")
                            # condition_price = {}
                            if len(conditions_list) >= 1:
                                # for item in sizes_list:
                                #     price = item.get("price").get(
                                #         "product", 0) / 100
                                #     condition_price[item.get(
                                #         "name")] = price
                                size = conditions_list[0].get("name")
                                price = conditions_list[0].get(
                                    "price").get("product", 0)

                        url_card = f"https://www.wildberries.ru/catalog/{pid}/detail.aspx"

                        rows.append({
                            "pid": pid,
                            "name": name,
                            "brand": brand,
                            "rating": rating,
                            "feedbacks": feedbacks,
                            "source": "search",
                            "url": url_card,
                            "price": price,
                            "query": query
                        })
                        added += 1
                        if len(rows) >= max_items:
                            # отключим слушатель, чтобы не забивать лишним
                            stop_collecting = True
                            return
                    except Exception as e:
                        print(f"Error extracting product ID: {e}")
                        continue
                if added > 0:
                    last_added_at = time.time()
            page.on("response", on_response)

            page.goto(
                "https://www.wildberries.ru/catalog/0/search.aspx?search=" +
                quote_plus(query),
                timeout=60_000,
            )

            # Дадим странице подгрузить результаты и проскроллим, чтобы подтянулись новые чанки
            page.wait_for_timeout(7000)
            prev_height = 0
            stagnant_rounds = 0            # сколько циклов подряд нет роста/новых товаров
            MAX_STAGNANT_ROUNDS = 6        # после этого — выходим
            MAX_TOTAL_TIME = 60            # секунд: страховка, чтобы не крутить бесконечно
            t0 = time.time()
            while len(rows) < max_items:
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(delay_ms)
                curr_height = page.evaluate("document.body.scrollHeight")
                if curr_height <= prev_height and time.time() - last_added_at > (delay_ms/1000) * 2:
                    stagnant_rounds += 1
                else:
                    stagnant_rounds = 0
                prev_height = curr_height
                if stagnant_rounds >= MAX_STAGNANT_ROUNDS:
                    break
                if time.time() - t0 > MAX_TOTAL_TIME:
                    break

            context.close()
            browser.close()

            if rows:
                init_db()
                saved = upsert_products(rows)
                print(f"Сохранено/обновлено в БД: {saved}")
            else:
                print(
                    "Не удалось собрать товары. Проверь поисковую фразу или попробуй перезапустить.")

    else:
        print("No search query provided.")


if __name__ == "__main__":
    main()
