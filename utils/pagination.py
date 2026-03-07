from math import ceil


def paginate(items, page, per_page=20):
    page = max(page, 1)

    total = len(items)
    pages = ceil(total / per_page)

    start = (page - 1) * per_page
    end = start + per_page

    return {
        "items": items[start:end],
        "page": page,
        "pages": pages,
        "total": total,
        "start": start + 1 if total else 0,
        "end": min(end, total)
    }
