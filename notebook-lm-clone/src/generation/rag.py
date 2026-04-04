import json
import logging
import re
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
    context_excerpt: Optional[str] = None
    
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

            result_metadata = result.get('metadata') or {}

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
                if result_metadata.get('gemini_caption'):
                    source_info['gemini_caption'] = result_metadata.get('gemini_caption')
                if result_metadata.get('image_content_type'):
                    source_info['image_content_type'] = result_metadata.get('image_content_type')
                if result_metadata.get('image_concepts'):
                    source_info['image_concepts'] = result_metadata.get('image_concepts')
                if result_metadata.get('gemini_confidence') is not None:
                    source_info['gemini_confidence'] = result_metadata.get('gemini_confidence')

            sources_info.append(source_info)
        
        formatted_context = '\n\n'.join(context_parts)

        return formatted_context, sources_info

    def _filter_context_by_topic(self, context: str, topic: Optional[str]) -> str:
        topic_text = (topic or "").strip().lower()
        if not topic_text or not context.strip():
            return context

        keywords = [token for token in re.split(r"[^a-z0-9]+", topic_text) if len(token) > 2]
        if not keywords:
            return context

        segments = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n{2,}", context) if segment.strip()]
        matched_segments = [segment for segment in segments if any(keyword in segment.lower() for keyword in keywords)]
        if not matched_segments:
            return context

        return "\n\n".join(matched_segments)

    def _normalize_question_types(self, question_types: Optional[List[str]]) -> List[str]:
        allowed = {
            "mcq": "mcq",
            "multiple choice": "mcq",
            "multiple_choice": "mcq",
            "short": "short",
            "short answer": "short",
            "short_answer": "short",
            "true_false": "true_false",
            "true/false": "true_false",
            "true false": "true_false",
            "fill_blank": "fill_blank",
            "fill in the blank": "fill_blank",
            "fill-in-the-blank": "fill_blank",
        }

        normalized: List[str] = []
        for item in question_types or []:
            key = str(item).strip().lower()
            mapped = allowed.get(key)
            if mapped and mapped not in normalized:
                normalized.append(mapped)

        return normalized or ["mcq"]

    def generate_quiz_from_config(self, config: Dict[str, Any]) -> RAGResult:
        number_of_questions = int(config.get("number_of_questions") or config.get("num_questions") or 5)
        number_of_questions = max(3, min(30, number_of_questions))

        difficulty = str(config.get("difficulty") or config.get("quiz_difficulty") or "mixed").strip().lower()
        if difficulty not in {"easy", "medium", "hard", "mixed"}:
            difficulty = "mixed"

        question_types = self._normalize_question_types(config.get("question_types"))
        topic = str(config.get("topic") or config.get("topic_focus") or "").strip()
        previous_questions = [
            str(question).strip()
            for question in (config.get("previous_questions") or config.get("existing_questions") or [])
            if str(question).strip()
        ]

        rag_context = str(config.get("rag_context") or "").strip()
        sources_info: List[Dict[str, Any]] = []
        retrieval_count = 0

        if not rag_context:
            retrieval_query = "concepts relationships applications reasoning trade-offs"
            if topic:
                retrieval_query = f"{topic} {retrieval_query}"

            query_vector = self.embedding_generator.generate_query_embedding(retrieval_query)
            search_results = self.vector_db.search(query_vector=query_vector.tolist(), limit=int(config.get("max_chunks") or 12))
            retrieval_count = len(search_results)

            if not search_results:
                return RAGResult(
                    query="Quiz",
                    response="No documents available.",
                    sources_used=[],
                    retrieval_count=0,
                )

            rag_context, sources_info = self._format_context_with_citations(search_results, int(config.get("max_chunks") or 12), 6000)
        else:
            rag_context = self._filter_context_by_topic(rag_context, topic)

        prompt = f"""You are an expert academic quiz generator for university-level students.

You must generate concept-driven questions that improve understanding, not memorization.

Course material comes from a RAG system and may include:
1. Conceptual text explanations
2. Table-derived descriptions converted to text
3. Diagram-derived descriptions converted to text

You must use ONLY the provided RAG context as the knowledge source.

STRICTLY FORBIDDEN:
1) Questions about document structure, units, modules, sections, or syllabi.
2) Questions that explicitly reference diagrams, figures, tables, or charts.
3) Questions that require unseen layout or image content.
4) Trivial recall questions or copied definitions.

WHAT TO DO:
1) Treat text as theory and explanation.
2) Treat table-derived text as comparisons, trends, and relationships.
3) Treat diagram-derived text as processes, flows, and systems.
4) Ask why, how, compare, apply, analyze, and reason questions.

DIFFICULTY LOGIC:
- easy: basic understanding
- medium: application and comparison
- hard: analysis, reasoning, multi-step thinking
- mixed: balanced across all levels

NON-REPETITION:
- Do not repeat any previous question.
- Do not test the same concept in the same way.
- Ensure diversity in concepts and phrasing.

SELF-VALIDATION:
Before outputting each question, ensure it:
- tests understanding rather than memory
- is answerable from the provided context
- does not mention modules, units, or structure
- does not reference visuals explicitly
- is different from previous questions
- if any check fails, rewrite it

INPUT CONFIG:
- number_of_questions: {number_of_questions}
- difficulty: {difficulty}
- question_types: {", ".join(question_types)}
- topic: {topic or "None"}

PREVIOUS QUESTIONS:
{chr(10).join(f"- {question}" for question in previous_questions) if previous_questions else "None"}

RAG CONTEXT:
{rag_context}

Return JSON only. Use this exact array schema:
[
  {{
    "id": "q1",
    "type": "mcq",
    "difficulty": "medium",
    "concept_tested": "concept name",
    "question": "question text",
    "options": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "correct_answer": "A",
    "explanation": "conceptual explanation"
  }}
]"""

        response = self.llm.call(prompt)
        return RAGResult(
            query="Quiz",
            response=response,
            sources_used=sources_info,
            retrieval_count=retrieval_count,
            context_excerpt=rag_context,
        )
    
    def _create_rag_prompt(self, query: str, context: str) -> str:
        prompt = f"""You are an AI Course Assistant focused on helping with coursework, assignments, and learning materials.

STRICT GUIDELINES:
1) Your default behavior is to answer using ONLY the provided context. Do not invent information.
2) If the context contains relevant information, answer concisely and stay on-topic.
3) Keep default answers short: maximum 4 bullet points or 120 words unless the user explicitly asks for a detailed explanation.
4) Prefer direct answers first, then brief supporting points.
5) If the context does NOT contain information to answer the question, reply: "I don't have information about this in the course materials."
6) ONLY refuse when the question is clearly unrelated to coursework or asks for personal information; in that case reply: "This application is specifically designed for course assistance. Your question is outside the scope of this course assistant. Please check other resources for this information."

CITATION REQUIREMENTS:
1) For each factual claim from the materials, include the citation reference number in square brackets [1], [2], etc.
2) Only use information from the provided context - do NOT add external knowledge or make assumptions.
3) If you cannot find relevant information in the context, use the message in guideline #5 above.
4) Be precise and accurate in your citations.
5) When multiple sources support the same point, list all relevant citations like [1], [2], [3].

CONTEXT (with citation references):
{context}

QUESTION: {query}

Provide a focused, concise answer using ONLY the course materials. If the context is insufficient, use the fallback message in guideline #5. If the question is clearly outside coursework, use the scope message in guideline #6."""

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
        difficulty: str = "Mixed",
        question_types: Optional[List[str]] = None,
        topic_focus: Optional[str] = None,
        existing_questions: Optional[List[str]] = None,
    ) -> RAGResult:
        return self.generate_quiz_from_config({
            "number_of_questions": num_questions,
            "max_chunks": max_chunks,
            "difficulty": difficulty,
            "question_types": question_types,
            "topic_focus": topic_focus,
            "existing_questions": existing_questions,
        })

    def generate_flashcards(
        self,
        num_cards: int = 10,
        max_chunks: int = 12,
        card_mode: str = "Question->Answer",
        topic_focus: Optional[str] = None,
        existing_cards: Optional[List[str]] = None,
    ) -> RAGResult:
        try:
            mode = (card_mode or "Question->Answer").strip()
            if mode not in {"Term->Definition", "Concept->Explanation", "Question->Answer"}:
                mode = "Question->Answer"

            focus = (topic_focus or "").strip()
            prior_cards = [c.strip() for c in (existing_cards or []) if isinstance(c, str) and c.strip()]

            retrieval_query = "definitions concepts terms relationships applications explanations"
            if focus:
                retrieval_query = f"{focus} {retrieval_query}"

            query_vector = self.embedding_generator.generate_query_embedding(
                retrieval_query
            )
            search_results = self.vector_db.search(
                query_vector=query_vector.tolist(), limit=max_chunks
            )
            if not search_results:
                return RAGResult(
                    query="Flashcards", response="No documents available.", sources_used=[], retrieval_count=0
                )
            context, sources_info = self._format_context_with_citations(search_results, max_chunks, 6000)
            prior_text = "\n".join([f"- {c}" for c in prior_cards]) if prior_cards else "None"
            focus_instruction = focus if focus else "Use the most relevant concepts from retrieved material."

            prompt = f"""You are an expert academic flashcard generator for university-level students.

Generate concept-driven flashcards that improve understanding rather than memorization.

RULES:
- Use only the provided context.
- Do not mention modules/sections/syllabus.
- Do not reference diagrams/figures/tables directly.
- Convert table/diagram-derived text into conceptual relationships, flows, and reasoning prompts.
- Avoid trivial one-word recall prompts.
- Do not repeat existing cards.

INPUT SETTINGS:
- Number of cards: {num_cards}
- Card mode: {mode}
- Topic focus: {focus_instruction}
- Existing cards (must not be repeated):
{prior_text}

Return ONLY valid JSON — no markdown, no explanation, no extra text.

Format:
[
  {{"front": "Question or term", "back": "Answer or definition"}}
]

COURSE MATERIAL (RAG):
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

            retrieval_query = f"{topic_label} main topics subtopics hierarchy structure relationships processes"
            query_vector = self.embedding_generator.generate_query_embedding(retrieval_query)
            search_results = self.vector_db.search(
                query_vector=query_vector.tolist(), limit=max_chunks
            )
            if not search_results:
                return RAGResult(
                    query="Mind Map", response="No documents available.", sources_used=[], retrieval_count=0
                )
            context, sources_info = self._format_context_with_citations(search_results, max_chunks, 6000)
            prompt = f"""You are an expert academic mind map architect.

Create a richly structured conceptual mind map that helps university students understand relationships, flow, and hierarchy.

STRICT RULES:
- Output ONLY valid JSON.
- Do not mention module/unit/section structure.
- Do not mention diagrams, figures, tables, or charts explicitly.
- Every node must be grounded in the provided course material.
- Use short labels (2-5 words).
- Root must represent the topic.
- Level 1 branches: 4 to 7 nodes.
- Level 2 nodes: 2 to 5 per branch.
- Level 3 nodes: 1 to 3 per sub-branch.

User Prompt:
Generate a mind map for the topic: "{topic_label}"

Learning objective: {objective_label}
Difficulty target: {difficulty_label}

COURSE MATERIAL:
{context}

Return JSON with this exact structure:
{{
  "id": "root",
  "label": "{topic_label}",
  "children": [
    {{
      "id": "branch_1",
      "label": "Main Idea",
      "children": [
        {{
          "id": "sub_1_1",
          "label": "Key Concept",
          "children": [
            {{"id": "leaf_1_1_1", "label": "Specific Detail", "children": []}}
          ]
        }}
      ]
    }}
  ]
}}"""
            response = self.llm.call(prompt)
            return RAGResult(query="Mind Map", response=response, sources_used=sources_info, retrieval_count=len(search_results))
        except Exception as e:
            logger.error(f"Error generating mindmap: {e}")
            fallback = {
                "id": "root",
                "label": topic_label if 'topic_label' in locals() else "Mind Map",
                "children": []
            }
            return RAGResult(query="Mind Map", response=json.dumps(fallback), sources_used=[], retrieval_count=0)

        def generate_session_feedback_report(
                self,
                session_questions: List[Dict[str, Any]],
                retrieved_context_chunks: Optional[List[str]] = None,
                topic: Optional[str] = None,
                course_name: Optional[str] = None,
                previous_score: Optional[float] = None,
        ) -> RAGResult:
                try:
                        topic_label = (topic or "General Topic").strip() or "General Topic"
                        course_label = (course_name or "Course Session").strip() or "Course Session"
                        previous_score_text = "None" if previous_score is None else str(round(float(previous_score), 2))

                        context_chunks = [
                                str(chunk).strip()
                                for chunk in (retrieved_context_chunks or [])
                                if str(chunk).strip()
                        ]
                        context_text = "\n\n".join(context_chunks[:20]) if context_chunks else "No additional context provided."

                        prompt = f"""You are a personalised academic feedback agent.

Goal:
- Transform quiz outcomes into actionable, concept-level feedback.
- Focus on conceptual understanding and learning improvement.

Input Metadata:
- Course: {course_label}
- Topic: {topic_label}
- Previous score (%): {previous_score_text}

Session Questions and Evaluations (JSON):
{json.dumps(session_questions)}

Retrieved Course Context:
{context_text}

Required output JSON schema:
{{
    "question_results": [
        {{
            "question_index": 1,
            "question": "string",
            "what_you_got_right": ["string"],
            "what_was_incorrect": [
                {{ "student_claim": "string", "correction": "string" }}
            ],
            "what_you_missed": ["string"],
            "question_tip": "string"
        }}
    ],
    "performance_summary": {{
        "overall_score": 0,
        "overall_percentage": 0,
        "fully_correct_count": 0,
        "partially_correct_count": 0,
        "incorrect_count": 0,
        "estimated_conceptual_coverage": "string",
        "one_sentence_assessment": "string"
    }},
    "strength_areas": [
        {{ "concept": "string", "evidence": "string", "acknowledgement": "string" }}
    ],
    "weak_areas": [
        {{ "concept": "string", "description": "string", "exposed_by": "string", "significance": "string" }}
    ],
    "improvement_plan": [
        {{
            "concept": "string",
            "study_suggestion": "string",
            "activity_type": "quiz",
            "difficulty_level": "Medium",
            "resource_type": "topic practice",
            "system_action": {{
                "action_type": "quiz",
                "label": "Practice this concept",
                "settings": {{ "topic": "string", "difficulty": "medium" }}
            }}
        }}
    ],
    "next_step": "string",
    "learning_trend": "improved"
}}

Rules:
1) Output only JSON, no markdown or explanation.
2) Use concise academic tone.
3) "what_was_incorrect" must show claim-vs-correction pairs.
4) "question_tip" must be one sentence.
5) "learning_trend" must be one of: improved, declined, stable.
6) Suggestions in improvement_plan must be actionable and specific.
"""

                        response = self.llm.call(prompt)
                        return RAGResult(
                                query="Session Feedback Report",
                                response=response,
                                sources_used=[],
                                retrieval_count=0,
                                context_excerpt=context_text,
                        )
                except Exception as e:
                        logger.error(f"Error generating session feedback report: {e}")
                        return RAGResult(
                                query="Session Feedback Report",
                                response=f"Error: {e}",
                                sources_used=[],
                                retrieval_count=0,
                        )


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