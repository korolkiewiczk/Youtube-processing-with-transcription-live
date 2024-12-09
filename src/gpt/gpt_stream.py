from openai import OpenAI
from keys import OPENAI_API_KEY

def get_completions_stream(userMessage, model, max_tokens, temperature, systemMessage=""):
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": systemMessage},
            {"role": "user", "content": userMessage}
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True
    )
    return response