from langchain_ollama import ChatOllama
import os

def call_ollama_server(system_msg:str, query:str, model_choice:str)->None:
    llm = ChatOllama(model=model_choice, temperature=0, base_url="http://localhost:11434")

    response = llm.invoke([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query}
        ])
    
    r_content = response.content
    print(r_content)
    out_file = open("../test_out_data/llama_server_response.txt", "w")

    out_file.write(r_content)

    out_file.close()

sys_m = "You are an expert clinician that must respond to simple questions about different diseases. When asked about a disease, explain the causes, symptoms, and treatments"
q_m = "What is Alzheimer's disease?"

print(os.getcwd())
call_ollama_server(sys_m, q_m, "llama3.1:70b")