from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import faiss
import pandas as pd
import numpy as np
import os


app = FastAPI(title="AI Health Article Recommendation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow frontend to call API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = "articles_full.json"

if not os.path.exists(DATA_PATH):
    raise FileNotFoundError("❌ Dataset not found! Please run generate_real_articles.py first.")

df = pd.read_json(DATA_PATH, orient="records")

# Validate essential columns
required_columns = ["title", "body_part", "condition", "content", "link"]
for col in required_columns:
    if col not in df.columns:
        raise KeyError(f"Missing required column: {col}")

# Combine fields for better embedding context
df["combined_text"] = (
    df["body_part"].astype(str)
    + " "
    + df["condition"].astype(str)
    + " "
    + df["title"].astype(str)
    + " "
    + df["content"].astype(str)
)


print(" Loading SentenceTransformer model: all-MiniLM-L6-v2 ...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Generate embeddings for all articles
print(" Generating embeddings for articles...")
embeddings = model.encode(
    df["combined_text"].tolist(),
    show_progress_bar=True,
    normalize_embeddings=True
).astype("float32")


dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)  # cosine similarity since normalized
index.add(embeddings)
print(f" {len(df)} articles loaded and indexed successfully!")


class UserInput(BaseModel):
    name: str
    age: int
    body_part: str
    condition: str

@app.post("/recommend")
def recommend_articles(user: UserInput):
    query_text = f"{user.body_part} {user.condition}"
    query_vec = model.encode([query_text], normalize_embeddings=True).astype("float32")

    # Search top 10 similar articles
    D, I = index.search(query_vec, k=10)

    results = []
    for idx in I[0]:
        article = df.iloc[idx]
        results.append({
            "title": article["title"],
            "body_part": article["body_part"],
            "condition": article["condition"],
            "link": article["link"],
            "content": article["content"][:400] + "...",
            "source": article.get("source", "Unknown"),
            "date": article.get("date", "N/A"),
        })

    return {
        "user": user.name,
        "message": f"Top 10 articles for {user.condition} related to {user.body_part}",
        "recommendations": results,
    }


@app.get("/")
def home():
    return {"message": "✅ AI Health Article Recommendation API is running successfully!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

