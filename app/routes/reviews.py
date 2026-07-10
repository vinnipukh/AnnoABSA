"""Review data and chat endpoints.

Migration target:
    GET /data/{idx}          → get_data()
    POST /review/{idx}/save  → save_review_triplets()
    POST /agent/chat         → agent_chat()
"""
