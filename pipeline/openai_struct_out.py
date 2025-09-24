from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
import json

# Set your API key
os.environ["OPENAI_API_KEY"] = "sk-..."  # Replace or use env variable

def call_openai_struct_out(system_msg: str, query: str, model_used: str = "gpt-4-1106-preview", use_structured_output: bool = True):
    llm = ChatOpenAI(model=model_used, temperature=0)

    if use_structured_output:
        json_schema = {
            "title": "report",
            "description": "Information of the molecular report",
            "type": "object",
            "properties": {}
        }

        try:
            field_definitions = system_msg.split("## JSON schema")[1].split("##")[0].split("\n")
        except IndexError:
            raise ValueError("Prompt is missing the '## JSON schema' section.")

        for field in field_definitions:
            if len(field.strip()) > 0 and field.strip()[0].isdigit():
                field_parts = field.split("/")
                if len(field_parts) < 2:
                    continue

                field_name_full = field_parts[0].strip()
                field_description = field_parts[1].strip()

                field_name = field_name_full[field_name_full.find('"') + 1 : field_name_full.rfind('"')]

                desc_lower = field_description.lower()
                if "list" in desc_lower:
                    field_type = "array"
                elif "dictionary" in desc_lower or "dict" in desc_lower:
                    field_type = "object"
                elif "int" in desc_lower or "number" in desc_lower:
                    field_type = "integer"
                else:
                    field_type = "string"

                json_schema["properties"][field_name] = {
                    "description": field_description,
                    "type": field_type
                }

        print("Using JSON schema for structured output:")
        print(json.dumps(json_schema, indent=2))

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_msg),
                ("human", "Use the given format to extract information from the following input: {query}")
            ]
        )

        structured_llm = llm.with_structured_output(json_schema)
        chain = prompt | structured_llm
        result = chain.invoke({"query": query})
        return result

    else:
        print("Using raw chat completion without structured output.")
        response = llm.invoke([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query}
        ])
        return response.content
