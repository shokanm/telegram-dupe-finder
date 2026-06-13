from __future__ import annotations
import hashlib
from datetime import datetime, timezone
import imagehash
from PIL import Image


def compute_md5(file_path: str) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_phash(file_path: str) -> str:
    # hash_size=16 → 256-bit hash, better differentiates templated images (e.g. Kaspi receipts)
    return str(imagehash.phash(Image.open(file_path), hash_size=16))


def hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
    return imagehash.hex_to_hash(hash1_hex) - imagehash.hex_to_hash(hash2_hex)


def _date_diff_days(date_a: str, date_b: str) -> int:
    """Returns absolute difference in days between two ISO date strings."""
    try:
        def parse(s: str) -> datetime:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        return abs((parse(date_a) - parse(date_b)).days)
    except Exception:
        return 0


def find_exact_duplicates(photos: list[dict]) -> list[tuple[dict, dict]]:
    by_hash: dict[str, list[dict]] = {}
    for p in photos:
        if p["file_hash"]:
            by_hash.setdefault(p["file_hash"], []).append(p)

    pairs = []
    for group in by_hash.values():
        if len(group) > 1:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    pairs.append((group[i], group[j]))
    return pairs


def find_similar_duplicates(photos: list[dict], threshold: int,
                             exact_hashes: set[str],
                             max_date_diff_days: int = 0) -> list[tuple[dict, dict, int]]:
    """
    Ищет похожие фото по 256-bit pHash (hash_size=16).
    max_date_diff_days: если > 0, пропускает пары с датами дальше этого порога.
    Возвращает тройки: (фото1, фото2, hamming_distance).
    """
    candidates = [p for p in photos
                  if p["phash"] and p["file_hash"] not in exact_hashes]

    similar_pairs = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            a, b = candidates[i], candidates[j]

            if max_date_diff_days > 0:
                diff = _date_diff_days(a.get("date", ""), b.get("date", ""))
                if diff > max_date_diff_days:
                    continue

            dist = hamming_distance(a["phash"], b["phash"])
            if dist <= threshold:
                similar_pairs.append((a, b, dist))

    return similar_pairs
