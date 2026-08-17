import asyncio
from nemoguardrails import LLMRails, RailsConfig
from deepeval.metrics import ContextualPrecisionMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

# Import your existing function without modifying rag_search.py
from rag.rag_search import search_knowledge_base


# Initialize NeMo Guardrails
rails_config = RailsConfig.from_path("./guardrails_config")
rails = LLMRails(rails_config)


async def run_guarded_rag(user_query: str) -> tuple[str, str]:
    """
    Executes input guardrails, retrieves context via search_knowledge_base,
    and runs output guardrails over the augmented response.
    """
    # Step 1: Validate input query
    input_check = await rails.generate_async(prompt=user_query)
    if "cannot process" in input_check:
        return input_check, ""

    # Step 2: Search FAISS Index using existing dictionary interface
    search_results = search_knowledge_base(user_query, top_k=3)
    
    # Extract string content from result dictionaries
    retrieved_docs = [res["content"] for res in search_results if "content" in res]
    context_str = "\n---\n".join(retrieved_docs) if retrieved_docs else "No relevant context found."

    # Step 3: Construct augmented prompt and generate guarded output
    augmented_prompt = f"Context:\n{context_str}\n\nUser Question:\n{user_query}"
    final_response = await rails.generate_async(prompt=augmented_prompt)

    return final_response, context_str


def evaluate_rag_pipeline(user_query: str, response: str, retrieved_context: str, expected_output: str):
    """
    Evaluates retrieval precision and answer faithfulness using DeepEval.
    """
    test_case = LLMTestCase(
        input=user_query,
        actual_output=response,
        retrieval_context=[retrieved_context],
        expected_output=expected_output
    )

    precision_metric = ContextualPrecisionMetric(threshold=0.7)
    faithfulness_metric = FaithfulnessMetric(threshold=0.7)

    precision_metric.measure(test_case)
    faithfulness_metric.measure(test_case)

    print("\n--- DeepEval Evaluation Results ---")
    print(f"Context Precision Score: {precision_metric.score}")
    print(f"Faithfulness Score:      {faithfulness_metric.score}")


# Local execution test
if __name__ == "__main__":
    test_query = "How do I perform API testing?"
    expected = "Verify request structure, status codes, payload parameters, and authorization."

    # Run guarded execution
    response, context = asyncio.run(run_guarded_rag(test_query))
    print(f"\nResponse:\n{response}")

    # Evaluate execution
    if context and context != "No relevant context found.":
        evaluate_rag_pipeline(test_query, response, context, expected)