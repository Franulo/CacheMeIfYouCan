from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from ibm_watsonx import generate_linkedin_post
from ibm_watsonx import generate_podcast_outline
from nyt_openai import run_nyt_openai_pipeline  # <-- import pipeline function
import os

app = Flask(__name__)
CORS(app)
os.environ['USE_FALLBACK'] = 'true'
# Dummy data
ARTICLES = [
    {
        "id": 1,
        "title": "Oracle expands cloud AI partnership",
        "summary": "Short summary Oracle expands cloud AI partnership...",
        "time": "4 min ago"
    },
    {
        "id": 2,
        "title": "FOMC signals readiness to keep policy restrictive",
        "summary": "Short summary FOMC signals readiness...",
        "time": "34 min ago"
    },
    {
        "id": 3,
        "title": "DeepSeek unveils efficient AI model",
        "summary": "Short summary DeepSeek unveils efficient AI model...",
        "time": "1 hour ago"
    }
]

DETAILS = {
    1: {
        "tags": ["Technology", "US Markets"],
        "overview": "Detailed overview about Oracle news...",
        "live_ticker": ["Oracle update 1", "Oracle update 2"]
    },
    2: {
        "tags": ["Economy"],
        "overview": "Detailed overview about FOMC news...",
        "live_ticker": ["FOMC update 1"]
    },
    3: {
        "tags": ["AI"],
        "overview": "Detailed overview about DeepSeek...",
        "live_ticker": ["DeepSeek update 1", "DeepSeek update 2"]
    }
}

@app.route('/search-news', methods=['POST'])
def search_news():
    data = request.get_json() or {}

    year = int(data.get("year", 2024))
    month = int(data.get("month", 1))
    custom_search = data.get("custom_search")
    tabType = data.get("tabType", "Daily")  # now expect tabType from Flutter

    try:
        result = run_nyt_openai_pipeline(
            year=year,
            month=month,
            custom_search=custom_search,
            tabType=tabType
        )
        print(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/article/<int:article_id>', methods=['GET'])
def article_detail(article_id):
    detail = DETAILS.get(article_id)
    if not detail:
        return jsonify({"error": "not found"}), 404
    return jsonify(detail)

@app.route('/generate-linkedin-post', methods=['POST'])
def linkedin_post():
    data = request.get_json()
    articles = data.get("articles", [])

    if not articles or not isinstance(articles, list):
        return jsonify({"error": "Please provide a list of articles"}), 400

    post_text = generate_linkedin_post(articles)
    return jsonify({"linkedin_post": post_text})

@app.route("/generate-podcast-pdf", methods=["POST"])
def generate_podcast_pdf():
    """
    Request body JSON example:
    {
        "articles": [
            {"title": "Market Rally Continues", "summary": "Stocks rose sharply..."},
            {"title": "Tech Earnings Report", "summary": "Tech companies reported strong earnings..."}
        ]
    }
    """
    data = request.get_json()
    if not data or "articles" not in data:
        return jsonify({"error": "Missing 'articles' in request body"}), 400

    # Step 1: Generate the podcast outline
    outline = generate_podcast_outline(data["articles"])

    # Step 2: Create PDF
    pdf_file = generate_pdf("Podcast Outline", outline, filename="podcast_outline.pdf")

    # Step 3: Send PDF to user
    return send_file(pdf_file, as_attachment=True, download_name="podcast_outline.pdf")


if __name__ == '__main__':
    app.run(debug=True)
