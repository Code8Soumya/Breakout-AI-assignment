# Telegram Bot with Google Gemini and DynamoDB

This project implements a Telegram bot that leverages the power of Google Gemini (via Langchain) for natural language processing and DynamoDB for user data persistence.  The bot offers a conversational interface, handles various message types (text, photos), and includes a web search functionality.

## Features

* **Conversational AI:**  The bot interacts with users in a friendly and engaging manner, using emojis and adapting its tone to the context.  It's powered by the Google Gemini language model.
* **Multi-Modal Input:**  The bot accepts both text and photo messages.  For photos, it uses the LLM to generate descriptions.
* **Web Search:** A dedicated `/search` command allows users to perform web searches using the Tavily search API.  The results, including top links, are summarized and presented to the user.
* **User Data Management:** User information (phone number, name, etc.) and chat history are securely stored in a DynamoDB database.  This ensures persistence and allows for personalized interactions.
* **Error Handling and Logging:** Robust error handling and comprehensive logging are implemented to ensure stability and facilitate debugging.

## Tech Stack

* **Programming Language:** Python
* **Frameworks/Libraries:**
    * **Telegram Bot API:** For creating and managing the Telegram bot.
    * **Langchain:** For interacting with the Google Gemini language model.
    * **Langchain Google GenAI:**  Specifically for using the Google Generative AI API.
    * **CrewAI:** For orchestrating the web search agent.
    * **Boto3:** For interacting with AWS DynamoDB.
    * **Cachetools:** For caching user messages to improve performance.
    * **Dotenv:** For securely managing environment variables.
* **Cloud Services:**
    * **AWS DynamoDB:**  Used as a NoSQL database to store user data and conversation history.
    * **Google Generative AI:** The large language model powering the conversational AI.
    * **Tavily:**  The search API used for the web search functionality.
