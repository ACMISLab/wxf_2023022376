import base64
from openai import OpenAI


def get_vllm_messages(vis_prompt,encoded_img,temperature=0.8, top_p=0.8):
    """
    调用 InternVL 模型统一接口
    messages: OpenAI 格式的 message 列表
    return: 模型返回的文本内容
    """

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": vis_prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encoded_img}"
                }
            }
        ]
    }]

    client = OpenAI(
        api_key="YOUR_API_KEY",
        base_url="base_url"
    )

    response = client.chat.completions.create(
        model="InternVL3_5-8B",
        messages=messages,
        temperature=temperature,
        top_p=top_p
    )

    return response.choices[0].message.content



