import requests


#本地部署
def get_messages(prompt):

    base_url = "base_url"
    data = {
        "model": "Qwen2.5-7B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1,
    }

    response = requests.post(f"{base_url}/v1/chat/completions", json=data, stream=False).json()
    content = response['choices'][0]['message']['content']

    return content
