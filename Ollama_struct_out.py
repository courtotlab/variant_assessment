from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json

def call_ollama_struct_out(system_msg:str, query:str, model_used:str)->dict:
    llm = ChatOllama(model=model_used, temperature=0)

    json_schema = {}
    json_schema["title"] = "report"
    json_schema["description"] = "Information of the molecular report"
    json_schema["type"] = "object"
    json_schema["properties"] = {}

    field_definitions = system_msg.split("## JSON schema")[1].split("##")[0].split("\n")

    for field in field_definitions:
        if len(field) > 0 and field[0].isdigit():
            field_parts = field.split("/")
            field_name_full = field_parts[0]
            field_description = field_parts[1]

            field_name = field_name_full[field_name_full.find('"') + 1 : len(field_name_full)-1]

            json_schema["properties"][field_name] = {"description":field_description.strip()}

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_msg),
            ("human", "Use the given format to extract information from the following input: {query}")
        ]
    )

    structured_llm = llm.with_structured_output(json_schema)

    chain = prompt | structured_llm

    result = chain.invoke({"query":query})

    return result