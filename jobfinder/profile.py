"""Diego's profile config — keywords, weights, target titles."""

# Target titles in order of fit
TARGET_TITLES = [
    "ai product manager",
    "ai systems lead",
    "ai architect",
    "head of ai",
    "ai solutions architect",
    "ai engineer",
    "ai lead",
    "llm engineer",
    "prompt engineer",
    "ai product lead",
    "machine learning engineer",
]

# Partial title keywords that still score points
TITLE_KEYWORDS = [
    "ai", "llm", "machine learning", "ml", "artificial intelligence",
    "prompt", "generative", "gpt", "product manager", "product lead",
]

# Search terms for job boards
SEARCH_TERMS = [
    "AI product manager",
    "head of AI",
    "AI engineer LLM",
    "AI architect",
    "AI systems lead",
    "prompt engineer",
]

# Remotive-specific search terms
REMOTIVE_SEARCH_TERMS = [
    "AI",
    "LLM",
    "prompt engineer",
    "machine learning product",
]

# Description keyword groups: name -> (weight, keywords)
KEYWORD_GROUPS = {
    "llm_core": (15, [
        "llm", "large language model", "gpt", "gpt-4", "claude", "gemini",
        "openai", "anthropic", "prompt engineering", "prompt design",
        "embeddings", "rag", "retrieval augmented", "fine-tuning", "fine tuning",
        "transformer", "tokens", "context window",
    ]),
    "ai_pipeline": (12, [
        "pipeline", "orchestration", "workflow", "data ingestion",
        "etl", "mlops", "model evaluation", "model selection",
        "api integration", "n8n", "langchain", "llamaindex",
        "vector database", "pinecone", "weaviate", "chroma",
    ]),
    "automation": (8, [
        "automation", "automate", "automated", "workflow automation",
        "process automation", "rpa", "no-code", "low-code",
        "integration", "api", "webhook",
    ]),
    "product": (8, [
        "product manager", "product management", "product lead",
        "product owner", "roadmap", "user research", "a/b test",
        "stakeholder", "cross-functional", "agile", "sprint",
    ]),
    "crypto_defi": (6, [
        "crypto", "blockchain", "defi", "web3", "token",
        "smart contract", "decentralized", "bitcoin", "ethereum",
    ]),
    "startup_signals": (5, [
        "startup", "early-stage", "series a", "series b",
        "founding", "founding team", "greenfield", "0 to 1",
        "zero to one", "build from scratch", "yc", "y combinator",
    ]),
    "builder_culture": (4, [
        "builder", "ship", "shipping", "move fast", "hands-on",
        "full-stack", "end-to-end", "own", "ownership",
        "scrappy", "lean", "self-starter",
    ]),
}

# Locations that disqualify a job (not actually remote)
REJECTED_LOCATIONS = [
    "must be in", "on-site only", "no remote", "hybrid only",
    "in-office", "office-based",
]

# Salary targets (USD/year)
SALARY_FLOOR = 80_000
SALARY_TARGET = 120_000
SALARY_STRETCH = 150_000
