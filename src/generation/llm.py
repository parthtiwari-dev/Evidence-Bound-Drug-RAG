"""
LLM Generator with Groq integration, citation extraction, and validation.
Generates answers from retrieved chunks with proper citations and logging.
"""

import re
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from groq import Groq
import tiktoken
from dotenv import load_dotenv

from src.models.schemas import RetrievedChunk, GeneratedAnswer
from src.generation.prompts import (
    build_system_prompt,
    build_user_prompt,
    build_few_shot_examples
)

# Force .env to override system environment variables
load_dotenv(override=True)


class LLMGenerator:
    """
    LLM Generator using Groq API for fast, free inference.
    
    Features:
    - Citation extraction and validation
    - Generation logging to JSONL
    - Cost tracking (always $0.00 for Groq)
    - Error handling with graceful fallbacks
    """
    
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.0,
        max_tokens: int = 500,
        log_dir: str = "logs/api"
    ):
        """
        Initialize LLM Generator with Groq client.
        
        Args:
            model: Groq model to use (default: llama-3.3-70b-versatile)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            log_dir: Directory for generation logs
        """
        self.client = Groq()  # Uses GROQ_API_KEY from environment
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Use GPT-4 tokenizer as approximation for token counting
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        
        # Setup logging
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "generation_log.jsonl"
        
        print(f"✅ LLMGenerator initialized")
        print(f"   Model: {self.model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Max tokens: {self.max_tokens}")
        print(f"   Log file: {self.log_file}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Approximate token count
        """
        return len(self.tokenizer.encode(text))
    
    def _call_groq(
        self,
        messages: List[Dict[str, str]]
    ) -> Tuple[str, int, int]:
        """
        Call Groq API with messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Tuple of (answer, input_tokens, output_tokens)
            
        Raises:
            Exception: If API call fails
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        answer = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        return answer, input_tokens, output_tokens
    
    def extract_citations(self, answer: str) -> List[int]:
        """
        Extract citation numbers from answer text.
        
        Looks for [1], [2], [3] patterns in the answer.
        
        Args:
            answer: Generated answer text
            
        Returns:
            List of unique citation numbers, sorted
        """
        # Regex pattern to find [1], [2], etc.
        citations = re.findall(r'\[(\d+)\]', answer)
        
        # Convert to integers, remove duplicates, sort
        return sorted(set(int(c) for c in citations))
    
    def validate_citations(
        self,
        answer: str,
        num_chunks: int
    ) -> Dict[str, any]:
        """
        Validate citations in answer.
        
        Checks for:
        - Missing citations (no [1], [2], etc. found)
        - Invalid citation numbers (e.g., [5] when only 3 chunks)
        - Citation [0] (citations start at [1])
        
        Args:
            answer: Generated answer text
            num_chunks: Number of chunks that were provided
            
        Returns:
            Dict with 'valid', 'issues', and 'citations_found' keys
        """
        citations = self.extract_citations(answer)
        
        issues = []
        
        # Check if any citations exist
        if not citations:
            issues.append("CRITICAL: No citations found in answer")
        
        # Check each citation is valid
        for cit in citations:
            if cit > num_chunks:
                issues.append(
                    f"HALLUCINATION: Citation [{cit}] but only {num_chunks} chunks provided"
                )
            if cit < 1:
                issues.append(
                    f"INVALID: Citation [{cit}] (citations start at [1])"
                )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "citations_found": citations
        }
    
    def map_citations_to_chunks(
        self,
        citations: List[int],
        chunks: List[RetrievedChunk]
    ) -> Tuple[List[str], List[str]]:
        """
        Map citation numbers to chunk IDs and authorities.
        
        Args:
            citations: List of citation numbers (e.g., [1, 2, 3])
            chunks: List of retrieved chunks
            
        Returns:
            Tuple of (cited_chunk_ids, authorities_used)
        """
        cited_chunk_ids = []
        authorities_used = []
        
        for cite_num in citations:
            # Citations are 1-indexed, list is 0-indexed
            if 1 <= cite_num <= len(chunks):
                chunk = chunks[cite_num - 1]
                cited_chunk_ids.append(chunk.chunk_id)
                
                # Track unique authorities
                if chunk.authority_family not in authorities_used:
                    authorities_used.append(chunk.authority_family)
        
        return cited_chunk_ids, authorities_used
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD.
        
        Groq is FREE with rate limits, so cost is always $0.00.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            float: Cost (always 0.0 for Groq)
        """
        return 0.0  # Groq is FREE!
    
    def detect_refusal(self, answer: str) -> bool:
        """
        Detect if answer is a refusal.
        
        Looks for common refusal phrases.
        
        Args:
            answer: Generated answer text
            
        Returns:
            bool: True if answer appears to be a refusal
        """
        refusal_phrases = [
            "cannot provide medical advice",
            "cannot answer this question",
            "requires consultation with",
            "contact your doctor",
            "I don't have information",
            "not in the provided documentation"
        ]
        
        answer_lower = answer.lower()
        return any(phrase in answer_lower for phrase in refusal_phrases)
    
    def log_generation(
        self,
        query: str,
        answer: str,
        chunks: List[RetrievedChunk],
        citations: List[int],
        cited_chunk_ids: List[str],
        validation: Dict,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
        is_refusal: bool,
        authorities_used: List[str]
    ):
        """
        Log generation to JSONL file.
        
        Matches the retrieval logging pattern from Day 6 (Caution B).
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer_preview": answer[:100] + "..." if len(answer) > 100 else answer,
            "chunks_retrieved": len(chunks),
            "chunks_cited": len(cited_chunk_ids),
            "citations_found": citations,
            "cited_chunk_ids": cited_chunk_ids,
            "authorities_used": authorities_used,
            "is_refusal": is_refusal,
            "validation_passed": validation["valid"],
            "validation_issues": validation["issues"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "model": self.model
        }
        
        # Append to JSONL file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def generate_answer(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        question_id: Optional[str] = None
    ) -> GeneratedAnswer:
        """
        Generate answer from query and retrieved chunks.
        
        Complete pipeline:
        1. Build messages (system + user prompts)
        2. Call Groq API
        3. Extract and validate citations
        4. Map citations to chunk IDs
        5. Log to JSONL
        6. Return GeneratedAnswer
        
        Args:
            query: User's question
            chunks: Retrieved chunks to use as context
            question_id: Optional question ID for tracking
            
        Returns:
            GeneratedAnswer: Complete answer with metadata
        """
        start_time = time.time()
        
        try:
            # 1. Build messages
            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(query, chunks)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 2. Call Groq API
            answer, input_tokens, output_tokens = self._call_groq(messages)
            
            # 3. Extract citations
            citations = self.extract_citations(answer)
            
            # 4. Validate citations
            validation = self.validate_citations(answer, len(chunks))
            
            # 5. Map citations to chunk IDs and authorities
            cited_chunk_ids, authorities_used = self.map_citations_to_chunks(
                citations, chunks
            )
            
            # 6. Calculate cost and latency
            cost_usd = self.calculate_cost(input_tokens, output_tokens)
            latency_ms = (time.time() - start_time) * 1000
            
            # 7. Detect refusal
            is_refusal = self.detect_refusal(answer)
            
            # 8. Log generation
            self.log_generation(
                query=query,
                answer=answer,
                chunks=chunks,
                citations=citations,
                cited_chunk_ids=cited_chunk_ids,
                validation=validation,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                is_refusal=is_refusal,
                authorities_used=authorities_used
            )
            
            # 9. Return GeneratedAnswer
            return GeneratedAnswer(
                question_id=question_id or f"q_{int(time.time())}",
                query=query,
                answer_text=answer,
                cited_chunk_ids=cited_chunk_ids,
                is_refusal=is_refusal,
                authorities_used=authorities_used,
                total_token_count=input_tokens + output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd
            )
            
        except Exception as e:
            # Error handling: Return error response
            latency_ms = (time.time() - start_time) * 1000
            
            error_answer = f"ERROR: Generation failed - {str(e)}"
            
            # Log error
            self.log_generation(
                query=query,
                answer=error_answer,
                chunks=chunks,
                citations=[],
                cited_chunk_ids=[],
                validation={"valid": False, "issues": [str(e)], "citations_found": []},
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                is_refusal=False,
                authorities_used=[]
            )
            
            return GeneratedAnswer(
                question_id=question_id or f"q_error_{int(time.time())}",
                query=query,
                answer_text=error_answer,
                cited_chunk_ids=[],
                is_refusal=False,
                authorities_used=[],
                total_token_count=0,
                latency_ms=latency_ms,
                cost_usd=0.0
            )


# Quick test function
def test_llm_generator():
    """Test LLMGenerator with a simple query"""
    from src.models.schemas import RetrievedChunk
    
    print("=" * 80)
    print("TESTING LLM GENERATOR")
    print("=" * 80)
    
    # Create generator
    generator = LLMGenerator()
    
    # Create mock chunks
    mock_chunks = [
        RetrievedChunk(
            chunk_id="test_chunk_001",
            document_id="fda_warfarin_label_2025",
            text="Warfarin is an anticoagulant that prevents blood clots. Common side effects include bleeding, bruising, nausea, and vomiting. Serious side effects may include severe bleeding requiring immediate medical attention.",
            score=0.95,
            rank=1,
            retriever_type="vector",
            authority_family="FDA",
            tier=1,
            year=2025,
            drug_names=["warfarin"]
        )
    ]
    
    # Test query
    query = "What are the common side effects of warfarin?"
    
    print(f"\n🔍 Query: {query}")
    print(f"📄 Chunks provided: {len(mock_chunks)}")
    
    # Generate answer
    print("\n⏳ Calling Groq API...")
    result = generator.generate_answer(query, mock_chunks)
    
    # Display results
    print(f"\n✅ ANSWER GENERATED!")
    print(f"\n📝 Answer:\n{result.answer_text}")
    print(f"\n📊 Metadata:")
    print(f"   - Cited chunks: {result.cited_chunk_ids}")
    print(f"   - Authorities: {result.authorities_used}")
    print(f"   - Is refusal: {result.is_refusal}")
    print(f"   - Tokens: {result.total_token_count}")
    print(f"   - Latency: {result.latency_ms:.2f}ms")
    print(f"   - Cost: ${result.cost_usd:.6f}")
    
    print("\n" + "=" * 80)
    print("✅ LLM GENERATOR TEST COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    # Run test when file is executed directly
    test_llm_generator()
