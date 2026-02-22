SIMILARITY_THRESHOLD = 0.5
MIN_RELEVANT_CHUNKS = 2


def evaluate_context(query, search_results):
    if not search_results or not search_results.get("documents"):
        return {
            "sufficient": False,
            "confidence": 0.0,
            "relevant_chunks": 0,
            "reason": "Khong tim thay tai lieu nao trong database"
        }

    documents = search_results["documents"][0]
    distances = search_results["distances"][0]

    relevant_count = sum(1 for d in distances if d <= SIMILARITY_THRESHOLD)

    avg_similarity = 1 - (sum(distances[:3]) / min(3, len(distances)))

    sufficient = (
        relevant_count >= MIN_RELEVANT_CHUNKS
        and avg_similarity > 0.4
    )

    if sufficient:
        reason = "Du context"
    else:
        reason = "Context khong du, can tim them tu nguon ngoai"

    return {
        "sufficient": sufficient,
        "confidence": round(avg_similarity, 3),
        "relevant_chunks": relevant_count,
        "reason": reason
    }