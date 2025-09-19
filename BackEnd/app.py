from flask import Flask, jsonify, request
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2/top-headlines"

app = Flask(__name__)

def get_top_headlines(country="us", category=None):
    """Fetch articles from NewsAPI."""
    params = {
        "apiKey": NEWS_API_KEY,
        "country": country
    }
    if category:
        params["category"] = category

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        return {"error": "Failed to fetch news", "status_code": response.status_code}

    data = response.json()
    return data.get("articles", [])

@app.route("/news", methods=["GET"])
def news():
    """Return JSON list of articles."""
    country = request.args.get("country", "us")
    category = request.args.get("category")  # optional
    articles = get_top_headlines(country=country, category=category)
    return jsonify(articles)


BASE_URL_EVERYTHING = "https://newsapi.org/v2/everything"

def get_articles_by_topic(topic, language="en", sort_by="publishedAt"):
    """Fetch articles by topic keyword."""
    params = {
        "apiKey": NEWS_API_KEY,
        "q": topic,  # keyword or phrase
        "language": language,
        "sortBy": sort_by,  # relevancy | popularity | publishedAt
        "pageSize": 10       # number of articles to fetch
    }
    response = requests.get(BASE_URL_EVERYTHING, params=params)

    if response.status_code != 200:
        return {"error": "Failed to fetch news", "status_code": response.status_code}

    data = response.json()
    return data.get("articles", [])

@app.route("/topic-news", methods=["GET"])
def topic_news():
    """Return JSON list of articles for a specific topic."""
    topic = request.args.get("topic")
    if not topic:
        return jsonify({"error": "Please provide a topic ?topic=keyword"}), 400

    articles = get_articles_by_topic(topic)
    # Optionally return only selected fields:
    cleaned_articles = [
        {
            "title": a["title"],
            "description": a["description"],
            "url": a["url"],
            "image": a["urlToImage"],
            "content": a["content"]  # This is the content snippet NewsAPI gives
        }
        for a in articles if a.get("title")
    ]
    return jsonify(cleaned_articles)


@app.route("/hallelujah")
def hallelujah():
    return "Hallelujah!"

if __name__ == "__main__":
    app.run(debug=True)