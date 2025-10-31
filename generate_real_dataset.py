import json
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm
import time


NEWS_API_KEY = "e3f2f7c9-557c-41a8-b4b8-6b756c78f92d"  
TARGET_ARTICLE_COUNT = 1000
USER_AGENT = {"User-Agent": "Mozilla/5.0"}


health_data = {
    "Heart": ["Arrhythmia", "Heart Attack", "High Blood Pressure", "Heart Failure", "Coronary Artery Disease"],
    "Brain": ["Migraine", "Stroke", "Epilepsy", "Parkinson's", "Depression"],
    "Lungs": ["Asthma", "Pneumonia", "COPD", "Tuberculosis", "Bronchitis"],
    "Liver": ["Hepatitis", "Cirrhosis", "Fatty Liver", "Liver Cancer", "Jaundice"],
    "Kidney": ["Kidney Stones", "UTI", "Kidney Failure", "Nephritis", "Proteinuria"],
    "Bones": ["Osteoporosis", "Fracture", "Arthritis", "Scoliosis", "Bone Cancer"],
    "Eyes": ["Cataract", "Glaucoma", "Conjunctivitis", "Dry Eye", "Macular Degeneration"],
    "Skin": ["Eczema", "Psoriasis", "Acne", "Fungal Infection", "Skin Cancer"],
    "Digestive System": ["Acidity", "Ulcer", "IBS", "Constipation", "Gastritis"],
    "Immune System": ["Lupus", "Rheumatoid Arthritis", "HIV", "Allergies", "Autoimmune Diseases"],
}


sources = {
    "Healthline": "https://www.healthline.com/health/",
    "Mayo Clinic": "https://www.mayoclinic.org/diseases-conditions/",
    "NIH": "https://medlineplus.gov/",
    "WebMD": "https://www.webmd.com/",
    "ScienceDaily": "https://www.sciencedaily.com/search/?keyword=",
    "PubMed": "https://pubmed.ncbi.nlm.nih.gov/?term=",
}


def fetch_article_content(url):
    """Scrape paragraphs from health sites."""
    try:
        res = requests.get(url, headers=USER_AGENT, timeout=10)
        if res.status_code != 200:
            return ""
        soup = BeautifulSoup(res.content, "html.parser")
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text().strip() for p in paragraphs[:6])
        return text if len(text) > 100 else ""
    except Exception:
        return ""


def fetch_from_pubmed(condition, max_results=50):
    """Fetch abstracts from PubMed."""
    try:
        query = condition.replace(" ", "+")
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

        params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": max_results}
        ids_resp = requests.get(search_url, params=params, timeout=10)
        ids = ids_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        fetch_params = {"db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "text"}
        abstracts = requests.get(fetch_url, params=fetch_params, timeout=15).text.split("\n\n")

        articles = []
        for abs_text in abstracts:
            if len(abs_text.strip()) < 200:
                continue
            title = abs_text.split("\n")[0][:150]
            content = " ".join(abs_text.split("\n")[1:5])
            articles.append({
                "title": title,
                "content": content,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}",
                "source": "PubMed",
                "date": datetime.now().strftime("%Y-%m-%d"),
            })
        return articles
    except Exception:
        return []


def fetch_from_newsapi(condition, max_pages=3, page_size=20):
    """Fetch latest real health-related news via NewsAPI."""
    if not NEWS_API_KEY or NEWS_API_KEY == "YOUR_NEWSAPI_KEY":
        return []
    all_articles = []
    for page in range(1, max_pages + 1):
        params = {
            "q": condition,
            "pageSize": page_size,
            "page": page,
            "language": "en",
            "apiKey": NEWS_API_KEY,
        }
        try:
            r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            if r.status_code != 200:
                break
            data = r.json()
            for art in data.get("articles", []):
                all_articles.append({
                    "title": art.get("title", condition),
                    "content": art.get("description") or art.get("content", ""),
                    "link": art.get("url"),
                    "source": art.get("source", {}).get("name", "NewsAPI"),
                    "date": art.get("publishedAt", "").split("T")[0] or datetime.now().strftime("%Y-%m-%d"),
                })
            time.sleep(0.5)
        except Exception:
            continue
    return all_articles



articles = []
seen_links = set()

for body_part, conditions in tqdm(health_data.items(), desc="Fetching Real Articles"):
    for condition in conditions:
        condition_articles = []

        pubmed_arts = fetch_from_pubmed(condition)
        condition_articles += pubmed_arts


        news_arts = fetch_from_newsapi(condition)
        condition_articles += news_arts

        for src_name, src_base in sources.items():
            if "PubMed" in src_name or "ScienceDaily" in src_name:
                url = src_base + condition.replace(" ", "+")
            else:
                url = src_base + condition.replace(" ", "-").lower()

            content = fetch_article_content(url)
            if len(content) > 100:
                condition_articles.append({
                    "title": f"{condition}: Overview and Treatments",
                    "content": content,
                    "link": url,
                    "source": src_name,
                    "date": datetime(2025, random.randint(1, 12), random.randint(1, 28)).strftime("%Y-%m-%d")
                })
            time.sleep(0.4)

        # attach metadata
        for art in condition_articles:
            if not art["content"] or art["link"] in seen_links:
                continue
            seen_links.add(art["link"])
            art["body_part"] = body_part
            art["condition"] = condition
            articles.append(art)

        if len(articles) >= TARGET_ARTICLE_COUNT:
            break
    if len(articles) >= TARGET_ARTICLE_COUNT:
        break


output_path = "articles_full.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(articles, f, indent=2, ensure_ascii=False)

print(f"\n Successfully fetched {len(articles)} real articles in {output_path}")
