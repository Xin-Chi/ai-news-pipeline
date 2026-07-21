"""去重:同一則新聞多家報,快報不該重複。

預設用輕量詞彙相似度(Jaccard),CI 跑得快、無需下載模型。
打開 USE_EMBEDDINGS 改用 BGE-M3 語意去重——這是你的強項,
面試可聊「語意去重 vs 字面去重,以及 CI 場景的模型啟動成本 trade-off」。
"""
USE_EMBEDDINGS = False
SIM_THRESHOLD = 0.6

def _tokens(title: str) -> set:
    return set(title.lower().split())

def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def _dedup_lexical(items: list) -> list:
    kept, kept_tokens = [], []
    for it in items:
        toks = _tokens(it["title"])
        if any(_jaccard(toks, kt) >= SIM_THRESHOLD for kt in kept_tokens):
            continue
        kept.append(it)
        kept_tokens.append(toks)
    return kept

def _dedup_embeddings(items: list) -> list:
    from sentence_transformers import SentenceTransformer, util
    model = SentenceTransformer("BAAI/bge-m3")
    emb = model.encode([it["title"] for it in items], normalize_embeddings=True)
    kept, kept_emb = [], []
    for it, e in zip(items, emb):
        if any(float(util.cos_sim(e, ke)) >= SIM_THRESHOLD for ke in kept_emb):
            continue
        kept.append(it); kept_emb.append(e)
    return kept

def deduplicate(items: list) -> list:
    return _dedup_embeddings(items) if USE_EMBEDDINGS else _dedup_lexical(items)
