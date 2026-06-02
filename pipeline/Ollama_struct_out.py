from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json

def call_ollama_struct_out(system_msg: str, queries:list[str], model_used: str):
    llm = ChatOllama(model=model_used, temperature=0, base_url="http://localhost:11439")
    print(llm)

    messages = [{"role": "system", "content": system_msg}]

    for q in queries:
        messages.append({"role":"user", "content":q})
    
     # Just do a raw chat completion (no enforced JSON structure)
    response = llm.invoke(messages)
    
    return response.content
    
"""
For testing connection
print(call_ollama_struct_out("You are a system designed to tell the definition of words given by the user",
                             "Please define the word 'genetics'",
                             "llama3.1:70b",
                             False))
"""
