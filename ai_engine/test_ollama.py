from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

def test_local_llm():
    print("Initializing Local Llama 3...")

    llm = ChatOllama(
        model="llama3",
        temperature=0.0, 
    )

    messages = [
        HumanMessage(content="Explain the concept of 'Habeas Corpus' in exactly one sentence.")
    ]

    print("Sending prompt. Waiting for generation...\n")

    try:
        response = llm.invoke(messages)
        print("✅ SUCCESS! Response from Local AI:")
        print(f"> {response.content}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_local_llm()