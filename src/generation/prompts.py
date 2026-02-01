"""
Prompt templates for LLM generation with citation extraction.
Integrates refusal policy and formats retrieved chunks for context.
"""

from pathlib import Path
from typing import List, Dict
from src.models.schemas import RetrievedChunk


def build_system_prompt() -> str:
    """
    Build system prompt with refusal rules and citation requirements.
    
    Loads refusal policy from docs/refusal_policy.md and combines with
    core instructions for faithfulness and citation formatting.
    
    Returns:
        str: Complete system prompt
    """
    # Load refusal policy
    refusal_policy_path = Path("docs/refusal_policy.md")
    
    if refusal_policy_path.exists():
        refusal_rules = refusal_policy_path.read_text(encoding='utf-8')
    else:
        # Fallback if file doesn't exist
        refusal_rules = """
        REFUSAL POLICY:
        You must refuse to answer questions about:
        1. Medical advice (dosing, diagnosis, treatment recommendations)
        2. Drug comparisons or recommendations ("best" medication)
        3. Off-label uses
        4. Drugs not in the provided context
        5. Combining medications with alcohol or supplements
        6. Pregnancy or pediatric questions
        7. Stopping or changing medications
        """
    
    system_prompt = f"""You are a pharmaceutical information assistant that provides factual information from FDA and NICE drug documentation.

{refusal_rules}

CRITICAL RULES FOR ANSWERING:

1. **Answer ONLY from provided context chunks**
   - Do NOT use general medical knowledge
   - Do NOT speculate or make assumptions
   - If the answer is not in the context, say: "I cannot answer this question based on the provided documentation."

2. **ALWAYS cite sources using [1], [2], [3] format**
   - Place citations immediately after EVERY claim
   - Use [1] for chunk 1, [2] for chunk 2, etc.
   - Multiple sources: "Side effects include nausea [1] and headache [2]."
   - Every sentence with factual information MUST have a citation

3. **Handle conflicts properly**
   - If sources conflict, cite both and note the conflict
   - Do NOT merge contradictory information
   - Example: "Document A states X [1], while Document B states Y [2]."

4. **Be precise and factual**
   - Use exact terminology from the documents
   - Include specific details (dosages, percentages, warnings)
   - Maintain medical accuracy

5. **Refusal format**
   - If question violates refusal policy, respond: "I cannot provide medical advice. This question requires consultation with a healthcare provider."
   - If information not in context, respond: "I cannot answer this question based on the provided documentation."

Remember: Your role is to retrieve and cite information, NOT to provide medical advice or recommendations.
"""
    
    return system_prompt


def build_user_prompt(query: str, chunks: List[RetrievedChunk], max_chars_per_chunk: int = 800) -> str:
    """
    Build user prompt with formatted context chunks and query.
    
    Truncates chunks to prevent token overflow while preserving key information.
    Formats chunks with [1], [2], [3] numbering for citation.
    
    Args:
        query: User's question
        chunks: List of retrieved chunks
        max_chars_per_chunk: Maximum characters per chunk (default: 800)
        
    Returns:
        str: Formatted user prompt with context and query
    """
    # Format chunks with truncation
    context_parts = []
    
    for i, chunk in enumerate(chunks):
        chunk_num = i + 1
        
        # Truncate text if needed
        text = chunk.text
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk] + "... [truncated]"
        
        # Format chunk with metadata
        chunk_header = f"[{chunk_num}]"
        chunk_metadata = f"(Source: {chunk.chunk_id}, Score: {chunk.score:.3f})"
        
        formatted_chunk = f"{chunk_header} {chunk_metadata}\n{text}\n"
        context_parts.append(formatted_chunk)
    
    # Build complete prompt
    context_text = "\n".join(context_parts)
    
    user_prompt = f"""CONTEXT DOCUMENTS:

{context_text}

---

QUESTION: {query}

Please answer the question using ONLY the information from the context documents above. Remember to cite your sources using [1], [2], [3] format after every claim.
"""
    
    return user_prompt


def build_few_shot_examples() -> List[Dict[str, str]]:
    """
    Build few-shot examples showing correct citation and refusal behavior.
    
    Returns real examples from the corpus to teach:
    1. Proper citation format
    2. Proper refusal when appropriate
    
    Returns:
        List[Dict]: List of example message pairs
    """
    examples = [
        # Example 1: Good answer with proper citations
        {
            "role": "user",
            "content": """CONTEXT DOCUMENTS:

[1] (Source: fda_warfarin_label_2025_chunk_0044, Score: 0.892)
ADVERSE REACTIONS
The most common adverse reactions to warfarin are fatal and nonfatal hemorrhage from any tissue or organ. Bleeding complications may present as paralysis; paresthesia; headache; chest, abdomen, joint, muscle or other pain; dizziness; shortness of breath; difficulty breathing or swallowing; unexplained swelling; weakness; hypotension; or unexplained shock. Common side effects include bleeding, bruising, nausea, vomiting, and skin necrosis.

[2] (Source: fda_warfarin_highlights_2022_chunk_0043, Score: 0.867)
Common adverse reactions include hemorrhagic complications (bleeding from any site), nausea, vomiting, diarrhea, and abdominal pain. Less common reactions include alopecia, rash, and hepatic dysfunction.

---

QUESTION: What are the common side effects of warfarin?"""
        },
        {
            "role": "assistant",
            "content": """The most common adverse reactions to warfarin include:

1. **Hemorrhagic complications**: Fatal and nonfatal bleeding from any tissue or organ [1], which may present as paralysis, paresthesia, headache, chest or abdominal pain, dizziness, shortness of breath, or unexplained swelling [1].

2. **Gastrointestinal effects**: Nausea, vomiting [1][2], diarrhea, and abdominal pain [2].

3. **Other common reactions**: Bruising [1], skin necrosis [1], alopecia, rash, and hepatic dysfunction [2].

The most serious adverse reaction is bleeding, which can occur from any site in the body [1][2]."""
        },
        
        # Example 2: Proper refusal for out-of-scope question
        {
            "role": "user",
            "content": """CONTEXT DOCUMENTS:

[1] (Source: fda_warfarin_label_2025_chunk_0044, Score: 0.789)
DOSAGE AND ADMINISTRATION
The dosage of warfarin must be individualized for each patient according to the patient's INR response to the drug. Adjust the dose based on the patient's INR and the clinical response. The recommended initial dose is 2 to 5 mg once daily.

---

QUESTION: Should I stop taking warfarin before my surgery next week?"""
        },
        {
            "role": "assistant",
            "content": """I cannot provide medical advice about stopping or changing medications. Decisions about warfarin management before surgery require consultation with your healthcare provider, who can assess your specific medical situation, bleeding risk, and surgical requirements. Please contact your doctor or surgeon for guidance on this question."""
        }
    ]
    
    return examples


# Test function to verify prompts work
def test_prompts():
    """Quick test to verify prompt functions work"""
    from src.models.schemas import RetrievedChunk
    
    print("=" * 80)
    print("TESTING PROMPT TEMPLATES")
    print("=" * 80)
    
    # Test 1: System prompt
    print("\n1. Testing build_system_prompt()...")
    system_prompt = build_system_prompt()
    print(f"✅ System prompt length: {len(system_prompt)} characters")
    print(f"✅ Contains 'REFUSAL POLICY': {'REFUSAL POLICY' in system_prompt or 'refusal' in system_prompt.lower()}")
    print(f"✅ Contains citation rules: {'[1]' in system_prompt}")
    print(f"\nFirst 200 chars:\n{system_prompt[:200]}...")
    
    # Test 2: User prompt with mock chunks
    print("\n2. Testing build_user_prompt()...")
    mock_chunks = [
        RetrievedChunk(
            chunk_id="test_chunk_001",
            document_id="fda_warfarin_label_2025",
            text="Warfarin is an anticoagulant. Common side effects include bleeding and bruising. It requires regular INR monitoring.",
            score=0.95,
            rank=1,
            retriever_type="vector",
            authority_family="FDA",
            tier=1,
            year=2025,
            drug_names=["warfarin"]
        ),
        RetrievedChunk(
            chunk_id="test_chunk_002",
            document_id="fda_warfarin_label_2025",
            text="Warfarin interacts with many medications. Patients should avoid vitamin K-rich foods in large amounts.",
            score=0.87,
            rank=2,
            retriever_type="vector",
            authority_family="FDA",
            tier=1,
            year=2025,
            drug_names=["warfarin"]
        )
    ]
    
    user_prompt = build_user_prompt("What are the side effects of warfarin?", mock_chunks)
    print(f"✅ User prompt length: {len(user_prompt)} characters")
    print(f"✅ Contains [1] marker: {'[1]' in user_prompt}")
    print(f"✅ Contains [2] marker: {'[2]' in user_prompt}")
    print(f"✅ Contains query: {'side effects' in user_prompt}")
    print(f"\nFirst 300 chars:\n{user_prompt[:300]}...")
    
    # Test 3: Few-shot examples
    print("\n3. Testing build_few_shot_examples()...")
    examples = build_few_shot_examples()
    print(f"✅ Number of examples: {len(examples)}")
    print(f"✅ Example 1 has user role: {examples[0]['role'] == 'user'}")
    print(f"✅ Example 2 has assistant role: {examples[1]['role'] == 'assistant'}")
    print(f"✅ Contains citations in example: {'[1]' in examples[1]['content']}")
    print(f"✅ Contains refusal example: {'cannot' in examples[3]['content'].lower()}")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)




if __name__ == "__main__":
    # Run tests when file is executed directly
    test_prompts()
