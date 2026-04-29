import argparse
import json
import os
from pathlib import Path
from typing import List

import torch
import torch.nn.functional as F

# 说明：
# 1. 这个脚本基于 i2i_encode.py 中现有的 get_model / encode 接口。
# 2. 请把它放在能够正确 import i2i_encode.py 的环境里执行。
# 3. 默认会递归扫描 key_dir 下所有图片，并返回与 query 最相似的 Top-K 文件名。

from i2i_encode import get_model, encode

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

# ===== 默认配置，按需修改 =====
DEFAULT_QUERY_PATH = r"F:\Code\MultiRetrievalSystem\data\i2i.jpg"
DEFAULT_KEY_DIR = r"F:\Code\MultiRetrievalSystem\data\ImageRetrieval"
DEFAULT_CKPT_PATH = "analyze_valid/base_distill_patchmask/augment_base_distill_float32_NWEP_RESISC45_256_2024-09-21-13-44-39/base_distill_NWEP_RESISC45_256_0.9648.pt"  # 例如：r"F:\Code\MultiRetrievalSystem\ckpts\i2i_model.pt"
DEFAULT_TOPK = 10


def collect_images(root_dir: str) -> List[str]:
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"key_dir not found: {root}")

    image_paths: List[str] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            image_paths.append(str(p))
    image_paths.sort()
    return image_paths


def compute_topk(query_path: str, key_dir: str, ckpt_path: str, topk: int = 10):
    if not os.path.isfile(query_path):
        raise FileNotFoundError(f"query image not found: {query_path}")

    key_paths = collect_images(key_dir)
    if len(key_paths) == 0:
        raise RuntimeError(f"no images found under key_dir: {key_dir}")

    if not ckpt_path:
        raise ValueError("ckpt_path is empty. Please set DEFAULT_CKPT_PATH or pass --ckpt-path.")

    print(f"[INFO] loading model from: {ckpt_path}")
    opt, model = get_model(ckpt_path=ckpt_path)

    print(f"[INFO] encoding query: {query_path}")
    query_feat = encode(opt, model, [query_path])
    if query_feat is None or len(query_feat) == 0:
        raise RuntimeError("failed to encode query image")

    print(f"[INFO] encoding {len(key_paths)} key images from: {key_dir}")
    key_feats = encode(opt, model, key_paths)
    if key_feats is None or len(key_feats) == 0:
        raise RuntimeError("failed to encode key images")

    # 归一化后做余弦相似度
    query_feat = F.normalize(query_feat.float(), p=2, dim=1)  # [1, D]
    key_feats = F.normalize(key_feats.float(), p=2, dim=1)  # [N, D]
    query_feat = query_feat.sign() / 256
    key_feats = key_feats.sign() / 256
    sims = torch.matmul(key_feats, query_feat[0])  # [N]

    k = min(topk, sims.shape[0])
    top_scores, top_indices = torch.topk(sims, k=k, dim=0, largest=True, sorted=True)

    results = []
    for rank, (score, idx) in enumerate(zip(top_scores.tolist(), top_indices.tolist()), start=1):
        img_path = key_paths[idx]
        results.append(
            {
                "rank": rank,
                "score": float(score),
                "file_name": os.path.basename(img_path),
                "file_path": img_path,
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description="Test i2i_encode.py and return Top-K similar image file names.")
    parser.add_argument("--query-path", type=str, default=DEFAULT_QUERY_PATH)
    parser.add_argument("--key-dir", type=str, default=DEFAULT_KEY_DIR)
    parser.add_argument("--ckpt-path", type=str, default=DEFAULT_CKPT_PATH)
    parser.add_argument("--topk", type=int, default=DEFAULT_TOPK)
    parser.add_argument("--save-json", type=str, default="")
    args = parser.parse_args()

    results = compute_topk(
        query_path=args.query_path,
        key_dir=args.key_dir,
        ckpt_path=args.ckpt_path,
        topk=args.topk,
    )

    print("\nTop-K similar file names:")
    for item in results:
        print(f"{item['rank']:>2}. {item['file_name']}\t score={item['score']:.6f}")

    if args.save_json:
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[INFO] saved json to: {args.save_json}")


if __name__ == "__main__":
    main()
