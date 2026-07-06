import os
from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    vs = client.vector_stores.create(name="optibot-support-docs")
    print(vs.id)


if __name__ == "__main__":
    main()