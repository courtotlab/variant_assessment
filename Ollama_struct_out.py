from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json

def call_ollama_struct_out(system_msg: str, query: str, model_used: str, use_structured_output: bool = True):
    llm = ChatOllama(model=model_used, temperature=0)

    if use_structured_output:
        json_schema = {
            "title": "report",
            "description": "Information of the molecular report",
            "type": "object",
            "properties": {}
        }

        try:
            # Extract JSON schema block from system_msg
            field_definitions = system_msg.split("## JSON schema")[1].split("##")[0].split("\n")
        except IndexError:
            raise ValueError("Prompt is missing the '## JSON schema' section.")

        for field in field_definitions:
            if len(field.strip()) > 0 and field.strip()[0].isdigit():
                field_parts = field.split("/")
                if len(field_parts) < 2:
                    continue  # Skip invalid lines

                field_name_full = field_parts[0].strip()
                field_description = field_parts[1].strip()

                # Extract field name between quotes
                field_name = field_name_full[field_name_full.find('"') + 1 : field_name_full.rfind('"')]

                # Guess type from description
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
        # Just do a raw chat completion (no enforced JSON structure)
        print("Using raw chat completion without structured output.")
        response = llm.invoke([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query}
        ])
        return response.content
