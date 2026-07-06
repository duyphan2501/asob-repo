import os
from openai import OpenAI
from utils.retry import openai_with_retry

SYSTEM_PROMPT = """
You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
"""

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")


def ask(question: str, vector_store_id: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    response = openai_with_retry(lambda: client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=question,
        tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],
    ))

    return response.output_text


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    vs_id = os.environ.get("VECTOR_STORE_ID")
    if not vs_id:
        sys.exit("No vector store found yet — run main.py first to scrape and upload docs.")

    question = sys.argv[1] if len(sys.argv) > 1 else "How do I add a YouTube video?"
    print(ask(question, vs_id))