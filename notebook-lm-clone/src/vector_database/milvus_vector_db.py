import logging
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

import chromadb
from src.embeddings.embedding_generator import EmbeddedChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MilvusVectorDB:
    def __init__(
        self, 
        db_path: str = "./chroma_db",
        collection_name: str = "notebook_lm",
        embedding_dim: int = 384
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.collection_exists = False
        self.chroma_client = None
        self.chroma_collection = None
        
        self._initialize_client()
        self._setup_collection()
    
    def _initialize_client(self):
        try:
            # Use ChromaDB
            chroma_path = str(Path(self.db_path).parent / "chroma_db") if not self.db_path.endswith("chroma_db") else self.db_path
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            logger.info(f"ChromaDB client initialized with database: {chroma_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise
    
    def _setup_collection(self):
        try:
            # ChromaDB setup
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB collection '{self.collection_name}' initialized")
            self.collection_exists = True
            
        except Exception as e:
            logger.error(f"Error setting up collection: {str(e)}")
            raise
    
    def create_index(self):
        """ChromaDB handles indexing automatically - no manual index creation needed"""
        logger.info("ChromaDB handles indexing automatically - skipping manual index creation")
        return
    
    def insert_embeddings(self, embedded_chunks: List[EmbeddedChunk]) -> List[str]:
        if not embedded_chunks:
            return []
        try:
            # ChromaDB insertion
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for embedded_chunk in embedded_chunks:
                chunk_data = embedded_chunk.to_vector_db_format()
                ids.append(chunk_data['id'])
                embeddings.append(chunk_data['vector'])
                documents.append(chunk_data['content'])
                
                # Filter out None values - ChromaDB doesn't accept them
                metadata = {
                    'source_file': chunk_data.get('source_file') or '',
                    'source_type': chunk_data.get('source_type') or 'unknown',
                    'page_number': chunk_data.get('page_number') if chunk_data.get('page_number') is not None else -1,
                    'chunk_index': chunk_data.get('chunk_index') if chunk_data.get('chunk_index') is not None else 0,
                    'start_char': chunk_data.get('start_char') if chunk_data.get('start_char') is not None else -1,
                    'end_char': chunk_data.get('end_char') if chunk_data.get('end_char') is not None else -1,
                    'embedding_model': chunk_data.get('embedding_model') or 'unknown',
                    'metadata': json.dumps(chunk_data.get('metadata') or {})
                }
                metadatas.append(metadata)
            
            self.chroma_collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Inserted {len(ids)} embeddings into ChromaDB")
            return ids
            
        except Exception as e:
            logger.error(f"Error inserting embeddings: {str(e)}")
            raise
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            # ChromaDB search
            results = self.chroma_collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )
            
            formatted_results = []
            if results and results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    metadata = results['metadatas'][0][i]
                    formatted_result = {
                        'id': results['ids'][0][i],
                        'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'content': results['documents'][0][i],
                        'citation': {
                            'source_file': metadata.get('source_file', ''),
                            'source_type': metadata.get('source_type', 'unknown'),
                            'page_number': metadata.get('page_number'),
                            'chunk_index': metadata.get('chunk_index', 0),
                            'start_char': metadata.get('start_char'),
                            'end_char': metadata.get('end_char'),
                        },
                        'metadata': json.loads(metadata.get('metadata', '{}')),
                        'embedding_model': metadata.get('embedding_model', 'unknown')
                    }
                    formatted_results.append(formatted_result)
            
            logger.info(f"ChromaDB search completed: {len(formatted_results)} results found")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            raise
    
    def delete_collection(self):
        try:
            self.chroma_client.delete_collection(name=self.collection_name)
            logger.info(f"ChromaDB collection '{self.collection_name}' deleted")
            self.collection_exists = False
                
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.collection_exists:
                logger.warning("Collection does not exist")
                return None
            
            logger.info(f"Attempting to retrieve chunk with ID: {chunk_id}")
            
            results = self.chroma_collection.get(
                ids=[chunk_id],
                include=['documents', 'metadatas']
            )
            
            if results and results['ids'] and len(results['ids']) > 0:
                metadata = results['metadatas'][0]
                return {
                    "id": results['ids'][0],
                    "content": results['documents'][0],
                    "metadata": json.loads(metadata.get('metadata', '{}')),
                    "source_file": metadata.get('source_file'),
                    "source_type": metadata.get('source_type'),
                    "page_number": metadata.get('page_number'),
                    "chunk_index": metadata.get('chunk_index', 0)
                }
            
            logger.warning(f"No chunk found with ID: {chunk_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving chunk by ID {chunk_id}: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            return None
    
    def close(self):
        """ChromaDB handles persistence automatically"""
        logger.info("ChromaDB connection closed")


if __name__ == "__main__":
    from src.document_processing.doc_processor import DocumentProcessor
    from src.embeddings.embedding_generator import EmbeddingGenerator
    
    doc_processor = DocumentProcessor()
    embedding_generator = EmbeddingGenerator()
    vector_db = MilvusVectorDB()
    
    try:
        chunks = doc_processor.process_document("data/raft.pdf")
        embedded_chunks = embedding_generator.generate_embeddings(chunks)
        vector_db.create_index()
        
        inserted_ids = vector_db.insert_embeddings(embedded_chunks)
        print(f"Inserted {len(inserted_ids)} embeddings")
        
        query_text = "What is the main topic?"
        query_vector = embedding_generator.generate_query_embedding(query_text)
        
        search_results = vector_db.search(query_vector.tolist(), limit=5)
        
        for i, result in enumerate(search_results):
            print(f"\nResult {i+1}:")
            print(f"Score: {result['score']:.4f}")
            print(f"Content: {result['content'][:200]}...")
            print(f"Citation: {result['citation']}")
        
    except Exception as e:
        print(f"Error in example: {e}")
    
    finally:
        vector_db.close()