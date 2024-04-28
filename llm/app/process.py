from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="ywhwang/SOLAR-10.7B-Instruct-v1.0-Q5_K_M",
    filename="SOLAR-10.7B-Instruct-v1.0.Q5_K_M.gguf",
    verbose=True,
)
llm.chat_format = "chatml"


def chat(ocr_pages: dict):
    responses = {}
    for pagenum, extracted_text in ocr_pages.items():
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are a server API that receives document information and returns its fields as a JSON object.",
                },
                {"role": "user", "content": f"{extracted_text}"},
            ],
            response_format={
                "type": "json_object",
            },
            temperature=0.7,
        )
        responses[pagenum] = response
    return responses


chat(
    {
        "page_1": "This is the first page of the document. It contains the first sentence of the document.",
    }
)
