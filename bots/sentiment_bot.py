import pandas as pd
from datetime import datetime, timedelta
import feedparser
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential


class SentimentBot:
    def __init__(self, num_results, rss_url, azure_endpoint, azure_key):
        self.latest_news = None
        self.news_sentiment = None
        self.num_results = num_results
        self.rss_url = rss_url
        self.client = self.authenticate_client(azure_endpoint, azure_key)
        self.update_news()
        self.analyse_sentiment()

    def authenticate_client(self, endpoint, key):
        return TextAnalyticsClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    def update_news(self):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            feed = feedparser.parse(self.rss_url)
            articles = []

            for entry in feed.entries:
                published_date = datetime(*entry.published_parsed[:6])

                if start_date <= published_date <= end_date:
                    headline = entry.title
                    articles.append({'date': published_date, 'headline': headline})

            df_articles = pd.DataFrame(articles)
            df_articles = df_articles.sort_values(by='date', ascending=False)
            self.latest_news = df_articles.head(self.num_results)
        except Exception:
            print("")

    def analyse_sentiment(self):
        try:
            sentiment_responses = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0

            for index, row in self.latest_news.iterrows():
                headline = row['headline']
                date = row['date']

                response = self.client.analyze_sentiment(documents=[headline], language="en")[0]

                if response.is_error:
                    print(f"Error analyzing sentiment for '{headline}': {response.error}")
                else:
                    sentiment_label = "POSITIVE" if response.confidence_scores["positive"] > 0.3 else "NEGATIVE" if \
                        response.confidence_scores["negative"] > 0.3 else "NEUTRAL"

                    sentiment_response = {
                        'date': date,
                        'headline': headline,
                        'sentiment': sentiment_label,
                        'confidence_scores': response.confidence_scores
                    }
                    sentiment_responses.append(sentiment_response)

                    if sentiment_label == "POSITIVE":
                        positive_count += 1
                    elif sentiment_label == "NEGATIVE":
                        negative_count += 1
                    else:
                        neutral_count += 1

            print("Number of positive articles:", positive_count)
            print("Number of negative articles:", negative_count)
            print("Number of neutral articles:", neutral_count)

            self.news_sentiment = sentiment_responses
            return sentiment_response
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return None

    def update(self):
        self.update_news()
        self.analyse_sentiment()

    def get_sentiment(self):
        return self.news_sentiment

    def get_overall_sentiment(self):
        try:
            overall_sentiment_score = 0

            for result in self.news_sentiment:
                sentiment = result['sentiment']
                if sentiment == "POSITIVE":
                    overall_sentiment_score += 0.5
                elif sentiment == "NEGATIVE":
                    overall_sentiment_score -= 0.5
            return overall_sentiment_score
        except Exception as e:
            print(f"Error calculating overall sentiment: {e}")
            return None


