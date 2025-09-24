from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json

def call_ollama_struct_out(system_msg: str, query: str, model_used: str) -> dict:
    llm = ChatOllama(model=model_used, temperature=0)

    json_schema = {
        "title": "report",
        "description": "Information of the molecular report",
        "type": "object",
        "properties": {}
    }

    try:
        # Extract JSON schema block
        field_definitions = system_msg.split("## JSON schema")[1].split("##")[0].split("\n")
    except IndexError:
        raise ValueError("Prompt is missing the '## JSON schema' section.")

    for field in field_definitions:
        field = field.strip()
        if not field or not field[0].isdigit():
            continue

        # Example line: 6. "quote_snippets" / list of strings.
        try:
            field_name_part, field_desc = field.split("/", 1)
        except ValueError:
            continue  # skip malformed lines

        field_name = field_name_part[field_name_part.find('"') + 1 : field_name_part.rfind('"')]
        field_desc = field_desc.strip().lower()

        # Determine field type
        if "list of strings" in field_desc:
            field_type = "array"
            item_type = "string"
        elif "list" in field_desc:
            field_type = "array"
            item_type = "object"  # fallback
        elif "dict" in field_desc or "dictionary" in field_desc:
            field_type = "object"
        elif "int" in field_desc or "integer" in field_desc or "number" in field_desc:
            field_type = "integer"
        else:
            field_type = "string"

        if field_type == "array":
            json_schema["properties"][field_name] = {
                "type": "array",
                "description": field_desc,
                "items": {"type": item_type}
            }
        else:
            json_schema["properties"][field_name] = {
                "type": field_type,
                "description": field_desc
            }

    print("🔧 Generated JSON Schema:\n", json.dumps(json_schema, indent=2))

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        ("human", "Use the given format to extract information from the following input: {query}")
    ])

    structured_llm = llm.with_structured_output(json_schema)
    chain = prompt | structured_llm

    result = chain.invoke({"query": query})
    return result
