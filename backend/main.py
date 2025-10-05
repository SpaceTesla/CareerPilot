from langchain_google_genai import ChatGoogleGenerativeAI

from config import models, settings


def main():
    chat = ChatGoogleGenerativeAI(
        model=models.FLASH,
        temperature=settings.temperature,
    )
    response = chat.invoke("Hello, how are you?")
    print(response)


if __name__ == "__main__":
    main()
