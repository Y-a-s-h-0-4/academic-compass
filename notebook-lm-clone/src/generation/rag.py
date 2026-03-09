import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from crewai import LLM
from src.vector_database.milvus_vector_db import MilvusVectorDB
from src.embeddings.embedding_generator import EmbeddingGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Represents the result of RAG generation with citations"""
    query: str
    response: str
    sources_used: List[Dict[str, Any]]
    retrieval_count: int
    generation_tokens: Optional[int] = None
    
    def get_citation_summary(self) -> str:
        if not self.sources_used:
            return "No sources cited"
        
        source_summary = []
        for source in self.sources_used:
            source_info = f"• {source.get('source_file', 'Unknown')} ({source.get('source_type', 'unknown')})"
            if source.get('page_number'):
                source_info += f" - Page {source['page_number']}"
            source_summary.append(source_info)
        
        return "\n".join(source_summary)


class RAGGenerator:
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        vector_db: MilvusVectorDB,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        self.embedding_generator = embedding_generator
        self.vector_db = vector_db

        selected_provider = (provider or "").strip().lower()
        if selected_provider in {"google", "gemini"}:
            selected_provider = "gemini"

        if not selected_provider:
            if gemini_api_key:
                selected_provider = "gemini"
            elif openai_api_key:
                selected_provider = "openai"

        if selected_provider not in {"openai", "gemini"}:
            raise ValueError("No supported LLM provider configured. Set GEMINI_API_KEY or OPENAI_API_KEY.")

        if selected_provider == "gemini" and not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when provider is gemini.")
        if selected_provider == "openai" and not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when provider is openai.")

        if model_name is None:
            model_name = "gemini-2.5-flash" if selected_provider == "gemini" else "gpt-4o-mini"

        model = model_name if "/" in model_name else f"{selected_provider}/{model_name}"
        api_key = gemini_api_key if selected_provider == "gemini" else openai_api_key
        
        self.llm = LLM(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
        )
        
        self.provider = selected_provider
        self.model_name = model_name
        logger.info(f"RAG Generator initialized with provider={selected_provider}, model={model}")
    
    def generate_response(
        self,
        query: str,
        max_chunks: int = 8,
        max_context_chars: int = 4000,
        top_k: int = 10,
    ) -> RAGResult:

        if not query.strip():
            return RAGResult(
                query=query,
                response="Please provide a valid question.",
                sources_used=[],
                retrieval_count=0
            )
        
        try:
            logger.info(f"Generating response for: '{query[:50]}...'")
            
            # Step 1: Retrieve relevant chunks
            query_vector = self.embedding_generator.generate_query_embedding(query)
            search_results = self.vector_db.search(
                query_vector=query_vector.tolist(),
                limit=top_k
            )
            
            if not search_results:
                return RAGResult(
                    query=query,
                    response="I couldn't find any relevant information in the available documents to answer your question.",
                    sources_used=[],
                    retrieval_count=0
                )
            
            # Step 2: Format context with citations
            context, sources_info = self._format_context_with_citations(
                search_results, max_chunks, max_context_chars
            )
            
            # Step 3: Create citation-aware prompt
            prompt = self._create_rag_prompt(query, context)
            
            # Step 4: Generate response
            response = self.llm.call(prompt)
            
            # Step 5: Create result object
            rag_result = RAGResult(
                query=query,
                response=response,
                sources_used=sources_info,
                retrieval_count=len(search_results)
            )
            
            logger.info(f"Response generated successfully using {len(sources_info)} sources")
            return rag_result
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return RAGResult(
                query=query,
                response=f"I encountered an error while processing your question: {str(e)}",
                sources_used=[],
                retrieval_count=0
            )
    
    def _format_context_with_citations(
        self,
        search_results: List[Dict[str, Any]],
        max_chunks: int,
        max_context_chars: int
    ) -> Tuple[str, List[Dict[str, Any]]]:

        context_parts = []
        sources_info = []
        total_chars = 0
        for i, result in enumerate(search_results[:max_chunks]):
            citation_info = result['citation']
            result_metadata = result.get('metadata') or {}
            source_file = citation_info.get('source_file', 'Unknown Source')
            source_type = citation_info.get('source_type', 'unknown')
            page_number = citation_info.get('page_number')
            
            citation_ref = f"[{i+1}]"
            chunk_content = result['content']
            chunk_text = f"{citation_ref} {chunk_content}"
            
            if total_chars + len(chunk_text) > max_context_chars and context_parts:
                break
            
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
            
            source_info = {
                'reference': citation_ref,
                'source_file': source_file,
                'source_type': source_type,
                'page_number': page_number,
                'chunk_id': result['id'],
                'relevance_score': result['score']
            }

            asset_type = result_metadata.get('asset_type')
            if asset_type in {'image', 'table'}:
                source_info['asset_type'] = asset_type
                source_info['asset_url'] = result_metadata.get('asset_url')
                source_info['asset_name'] = result_metadata.get('asset_name')

            if asset_type == 'table' and result_metadata.get('table_preview'):
                source_info['table_preview'] = result_metadata.get('table_preview')

            if asset_type == 'image':
                source_info['image_width'] = result_metadata.get('image_width')
                source_info['image_height'] = result_metadata.get('image_height')

            sources_info.append(source_info)
        
        formatted_context = '\n\n'.join(context_parts)

        return formatted_context, sources_info
    
    def _create_rag_prompt(self, query: str, context: str) -> str:
        prompt = f"""You are an AI Course Assistant focused on helping with coursework, assignments, and learning materials.

STRICT GUIDELINES:
1) Your default behavior is to answer using ONLY the provided context. Do not invent information.
2) If the context contains relevant information, answer concisely and stay on-topic.
3) If the context does NOT contain information to answer the question, reply: "I don't have information about this in the course materials."
4) ONLY refuse when the question is clearly unrelated to coursework or asks for personal information; in that case reply: "This application is specifically designed for course assistance. Your question is outside the scope of this course assistant. Please check other resources for this information."

CITATION REQUIREMENTS:
1) For each factual claim from the materials, include the citation reference number in square brackets [1], [2], etc.
2) Only use information from the provided context - do NOT add external knowledge or make assumptions.
3) If you cannot find relevant information in the context, use the message in guideline #3 above.
4) Be precise and accurate in your citations.
5) When multiple sources support the same point, list all relevant citations like [1], [2], [3].

CONTEXT (with citation references):
{context}

QUESTION: {query}

Provide a focused answer using ONLY the course materials. If the context is insufficient, use the fallback message in guideline #3. If the question is clearly outside coursework, use the scope message in guideline #4."""

        return prompt
    
    def generate_summary(
        self,
        max_chunks: int = 15,
        summary_length: str = "medium"
    ) -> RAGResult:
        try:
            summary_query = "main topics key findings important information overview"
            query_vector = self.embedding_generator.generate_query_embedding(summary_query)
            search_results = self.vector_db.search(
                query_vector=query_vector.tolist(),
                limit=max_chunks
            )
            
            if not search_results:
                return RAGResult(
                    query="Document Summary",
                    response="No documents available for summarization.",
                    sources_used=[],
                    retrieval_count=0
                )
            
            context, sources_info = self._format_context_with_citations(
                search_results, max_chunks, 6000
            )
            
            length_instructions = {
                'short': "Provide a concise 2-3 paragraph summary highlighting the most important points.",
                'medium': "Provide a comprehensive 4-5 paragraph summary covering key topics and findings.",
                'long': "Provide a detailed summary with multiple sections covering all major topics and supporting details."
            }
            
            summary_prompt = f"""You are tasked with creating a summary of the provided document content. Follow these guidelines:

1. {length_instructions.get(summary_length, length_instructions['medium'])}
2. Include citations [1], [2], etc. for all factual claims
3. Organize information logically with clear topics
4. Focus on the most important and relevant information
5. Maintain accuracy and cite sources properly

DOCUMENT CONTENT (with citation references):
{context}

Please provide a well-structured summary with proper citations:"""
            
            response = self.llm.call(summary_prompt)
            
            return RAGResult(
                query="Document Summary",
                response=response,
                sources_used=sources_info,
                retrieval_count=len(search_results)
            )
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return RAGResult(
                query="Document Summary",
                response=f"Error generating summary: {str(e)}",
                sources_used=[],
                retrieval_count=0
            )

    def generate_quiz(
        self,
        num_questions: int = 5,
        max_chunks: int = 12,
    ) -> RAGResult:
        try:
            query_vector = self.embedding_generator.generate_query_embedding(
                "key concepts definitions important facts exam topics"
            )
            search_results = self.vector_db.search(
                query_vector=query_vector.tolist(), limit=max_chunks
            )
            if not search_results:
                return RAGResult(
                    query="Quiz", response="No documents available.", sources_used=[], retrieval_count=0
                )
            context, sources_info = self._format_context_with_citations(search_results, max_chunks, 6000)
            prompt = f"""Generate exactly {num_questions} multiple-choice questions from the following study material.

Return ONLY valid JSON — no markdown, no explanation, no extra text.

Format:
[
  {{
    "question": "...",
    "options": [
      {{"id": "a", "text": "...", "isCorrect": false}},
      {{"id": "b", "text": "...", "isCorrect": true}},
      {{"id": "c", "text": "...", "isCorrect": false}},
      {{"id": "d", "text": "...", "isCorrect": false}}
    ],
    "explanation": "Brief explanation of the correct answer"
  }}
]

STUDY MATERIAL:
{context}"""
            response = self.llm.call(prompt)
            return RAGResult(query="Quiz", response=response, sources_used=sources_info, retrieval_count=len(search_results))
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return RAGResult(query="Quiz", response=f"Error: {e}", sources_used=[], retrieval_count=0)

    def generate_flashcards(
        self,
        num_cards: int = 10,
        max_chunks: int = 12,
    ) -> RAGResult:
        try:
            query_vector = self.embedding_generator.generate_query_embedding(
                "definitions concepts terms important facts explanations"
            )
            search_results = self.vector_db.search(
                query_vector=query_vector.tolist(), limit=max_chunks
            )
            if not search_results:
                return RAGResult(
                    query="Flashcards", response="No documents available.", sources_used=[], retrieval_count=0
                )
            context, sources_info = self._format_context_with_citations(search_results, max_chunks, 6000)
            prompt = f"""Generate exactly {num_cards} flashcards from the study material below.

Return ONLY valid JSON — no markdown, no explanation, no extra text.

Format:
[
  {{"front": "Question or term", "back": "Answer or definition"}}
]

STUDY MATERIAL:
{context}"""
            response = self.llm.call(prompt)
            return RAGResult(query="Flashcards", response=response, sources_used=sources_info, retrieval_count=len(search_results))
        except Exception as e:
            logger.error(f"Error generating flashcards: {e}")
            return RAGResult(query="Flashcards", response=f"Error: {e}", sources_used=[], retrieval_count=0)

    def generate_mindmap(
        self,
        max_chunks: int = 12,
        topic: Optional[str] = None,
        difficulty_level: str = "Intermediate",
        learning_objective: Optional[str] = None,
    ) -> RAGResult:
        try:
            topic_label = (topic or "Retrieved Course Topic").strip() or "Retrieved Course Topic"
            objective_label = (
                (learning_objective or "Understand key concepts, dependencies, and applications from the retrieved material.").strip()
                or "Understand key concepts, dependencies, and applications from the retrieved material."
            )
            difficulty_label = (difficulty_level or "Intermediate").strip() or "Intermediate"

            query_vector = self.embedding_generator.generate_query_embedding(
                f"{topic_label} {objective_label} main topics subtopics hierarchy structure prerequisites relationships examples formulas"
            )
            search_results = self.vector_db.search(
                query_vector=query_vector.tolist(), limit=max_chunks
            )
            if not search_results:
                return RAGResult(
                    query="Mind Map", response="No documents available.", sources_used=[], retrieval_count=0
                )
            context, sources_info = self._format_context_with_citations(search_results, max_chunks, 6000)
            prompt = f"""You are a mind map generation expert for an educational RAG system.
Generate comprehensive, well-structured mind maps that transform academic content into visual, hierarchical knowledge structures optimized for student learning.

INPUTS:
- Topic/Title: {topic_label}
- Source Content: RAG-retrieved material below with citations [1], [2], ...
- Difficulty Level: {difficulty_label}
- Learning Objective: {objective_label}

STRICT REQUIREMENTS:
1) Use ONLY facts grounded in the provided source content. No hallucinations.
2) Use domain-accurate terminology from the sources.
3) Hierarchy depth must be 3-4 levels maximum.
4) Central node + 4-7 primary branches.
5) Each primary branch has 2-4 sub-branches.
6) Node labels must be short phrases (1-3 words).
7) Include prerequisites, quiz anchors, revision hooks, and labeled relationships.
8) Include 1-2 real-world applications.
9) Include formulas/equations when relevant.
10) Ensure balance and logical progression from foundational to advanced.

OUTPUT FORMAT:
Return ONLY valid JSON (no markdown, no prose outside JSON) with this exact top-level structure:
{{
    "mindmap": {{
        "title": "...",
        "difficulty_level": "Basic|Intermediate|Advanced",
        "learning_objective": "...",
        "central_node": {{
            "text": "...",
            "description": "...",
            "source_refs": ["[1]"]
        }},
        "branches": [
            {{
                "id": "branch-1",
                "level": 2,
                "text": "...",
                "description": "...",
                "source_refs": ["[1]", "[2]"],
                "sub_branches": [
                    {{
                        "id": "branch-1-sub-1",
                        "level": 3,
                        "text": "...",
                        "details": "...",
                        "source_refs": ["[2]"],
                        "connections": [
                            {{ "to": "branch-2-sub-1", "relationship": "depends-on" }}
                        ],
                        "leaf_nodes": [
                            {{
                                "id": "branch-1-sub-1-leaf-1",
                                "level": 4,
                                "text": "...",
                                "details": "...",
                                "source_refs": ["[3]"]
                            }}
                        ]
                    }}
                ]
            }}
        ],
        "learning_notes": {{
            "prerequisites": ["..."],
            "quiz_anchors": ["..."],
            "revision_hooks": ["..."],
            "key_relationships": ["A -> B (depends-on)"]
        }},
        "validation_checklist": {{
            "all_information_sourced": true,
            "no_contradictions": true,
            "central_topic_clear": true,
            "primary_branch_count_valid": true,
            "short_node_labels": true,
            "real_world_examples_included": true,
            "learning_objectives_addressed": true,
            "prerequisites_identified": true,
            "relationships_labeled": true,
            "depth_within_limits": true,
            "terminology_matches_sources": true
        }},
        "evaluation_metrics": {{
            "accuracy": 0,
            "completeness": 0,
            "clarity": 0,
            "structure": 0,
            "usability": 0
        }}
    }},
    "mermaid": "mindmap\\n  root((Topic))\\n    BranchA\\n      SubA",
    "ascii": "Topic\\n|- Branch A\\n|  |- Sub A",
    "render_tree": {{
        "id": "root",
        "label": "...",
        "children": [
            {{
                "id": "branch-1",
                "label": "...",
                "children": [
                    {{ "id": "branch-1-sub-1", "label": "...", "children": [] }}
                ]
            }}
        ]
    }}
}}

VALIDATION TARGETS:
- 4-7 primary branches
- 2-4 sub-branches per primary branch
- 1-3 words per node label
- 3-4 depth levels maximum
- include source_refs for factual nodes
- include at least 2 real-world applications when supported by sources

SOURCE MATERIAL (use citations exactly as provided):
{context}

Generate the JSON now."""
            response = self.llm.call(prompt)
            return RAGResult(query="Mind Map", response=response, sources_used=sources_info, retrieval_count=len(search_results))
        except Exception as e:
            logger.error(f"Error generating mindmap: {e}")
            return RAGResult(query="Mind Map", response=f"Error: {e}", sources_used=[], retrieval_count=0)


if __name__ == "__main__":
    import os
    from src.document_processing.doc_processor import DocumentProcessor
    from src.embeddings.embedding_generator import EmbeddingGenerator
    from src.vector_database.milvus_vector_db import MilvusVectorDB
    
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not openai_key and not gemini_key:
        print("Please set GEMINI_API_KEY or OPENAI_API_KEY environment variable")
        exit(1)
    
    try:
        embedding_gen = EmbeddingGenerator()
        vector_db = MilvusVectorDB()
        rag_generator = RAGGenerator(
            embedding_generator=embedding_gen,
            vector_db=vector_db,
            openai_api_key=openai_key,
            gemini_api_key=gemini_key,
            temperature=0.1
        )
        
        test_query = "What are the main findings discussed in the documents?"
        result = rag_generator.generate_response(test_query)
        
        print(f"Query: {result.query}")
        print(f"Response: {result.response}")
        print(f"\nSources Used ({len(result.sources_used)}):")
        print(result.get_citation_summary())
        
        summary_result = rag_generator.generate_summary(summary_length="medium")
        print(f"\nDocument Summary:")
        print(summary_result.response)
        
    except Exception as e:
        print(f"Error in RAG pipeline example: {e}")