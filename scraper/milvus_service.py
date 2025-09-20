"""
Milvus Lite vector database service for storing and querying embeddings.
Optimized for high-performance similarity search with minimal metadata overhead.
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType,
    utility, MilvusException
)
from django.conf import settings

logger = logging.getLogger(__name__)


class MilvusService:
    """
    Service for managing Milvus Lite vector database operations.
    Optimized for storing document embeddings with minimal metadata overhead.
    """

    def __init__(self):
        self.db_path = settings.MILVUS_DB_PATH or "./milvus_lite.db"
        self.collection_name = "document_embeddings"
        self.vector_dim = 3072  # text-embedding-large-3 dimensions

        # Connect to Milvus Lite
        self._connect()
        self._ensure_collection()

    def _connect(self):
        """Connect to Milvus Lite database."""
        try:
            connections.connect(
                alias="default",
                uri=self.db_path
            )
            logger.info(f"Connected to Milvus Lite at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus Lite: {str(e)}")
            raise

    def _ensure_collection(self):
        """Ensure the embeddings collection exists with optimal schema."""
        try:
            # Check if collection exists
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Using existing collection: {self.collection_name}")
            else:
                # Create collection with minimal metadata schema
                fields = [
                    FieldSchema(
                        name="id",
                        dtype=DataType.VARCHAR,
                        max_length=255,
                        is_primary=True
                    ),
                    FieldSchema(
                        name="embedding",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=self.vector_dim
                    ),
                    FieldSchema(
                        name="summary_id",
                        dtype=DataType.VARCHAR,
                        max_length=255,
                        description="Reference to the summary in Django DB"
                    ),
                    FieldSchema(
                        name="url",
                        dtype=DataType.VARCHAR,
                        max_length=2000,
                        description="Original URL of the document"
                    ),
                    FieldSchema(
                        name="domain",
                        dtype=DataType.VARCHAR,
                        max_length=255,
                        description="Domain of the document"
                    ),
                    FieldSchema(
                        name="created_at",
                        dtype=DataType.VARCHAR,
                        max_length=50,
                        description="Creation timestamp"
                    )
                ]

                schema = CollectionSchema(
                    fields=fields,
                    description="Document embeddings for semantic search"
                )

                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema
                )

                # Create index for fast similarity search
                index_params = {
                    "metric_type": "COSINE",  # Cosine similarity for semantic search
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024}
                }

                self.collection.create_index(
                    field_name="embedding",
                    index_params=index_params
                )

                logger.info(f"Created new collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Error setting up collection: {str(e)}")
            raise

    def insert_embedding(self, embedding_data: Dict[str, Any]) -> str:
        """
        Insert a single embedding into the database.

        Args:
            embedding_data: Dictionary containing embedding and metadata

        Returns:
            ID of the inserted embedding
        """
        try:
            embedding_id = embedding_data.get('embedding_id', '')
            embedding_vector = embedding_data.get('embedding_vector', [])
            summary_id = embedding_data.get('summary_id', '')
            url = embedding_data.get('url', '')
            domain = embedding_data.get('domain', '')
            created_at = embedding_data.get('created_at', datetime.now().isoformat())

            # Prepare data for insertion
            data = [
                [embedding_id],  # id
                [embedding_vector],  # embedding
                [summary_id],  # summary_id
                [url],  # url
                [domain],  # domain
                [created_at]  # created_at
            ]

            # Insert data
            result = self.collection.insert(data)
            self.collection.flush()  # Ensure data is written

            logger.info(f"Inserted embedding {embedding_id}")
            return embedding_id

        except Exception as e:
            logger.error(f"Error inserting embedding: {str(e)}")
            raise

    def insert_embeddings_batch(self, embeddings_data: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple embeddings in batch for better performance.

        Args:
            embeddings_data: List of embedding dictionaries

        Returns:
            List of inserted embedding IDs
        """
        try:
            if not embeddings_data:
                return []

            # Prepare batch data
            ids = []
            embeddings = []
            summary_ids = []
            urls = []
            domains = []
            created_ats = []

            for data in embeddings_data:
                ids.append(data.get('embedding_id', ''))
                embeddings.append(data.get('embedding_vector', []))
                summary_ids.append(data.get('summary_id', ''))
                urls.append(data.get('url', ''))
                domains.append(data.get('domain', ''))
                created_ats.append(data.get('created_at', datetime.now().isoformat()))

            # Insert batch
            batch_data = [ids, embeddings, summary_ids, urls, domains, created_ats]
            result = self.collection.insert(batch_data)
            self.collection.flush()

            inserted_ids = ids  # In batch insert, we control the IDs
            logger.info(f"Inserted {len(inserted_ids)} embeddings in batch")
            return inserted_ids

        except Exception as e:
            logger.error(f"Error inserting embeddings batch: {str(e)}")
            raise

    def search_similar(self, query_embedding: List[float], limit: int = 10,
                      domain_filter: str = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results to return
            domain_filter: Optional domain filter

        Returns:
            List of similar documents with metadata
        """
        try:
            # Prepare search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }

            # Build filter expression
            filter_expr = ""
            if domain_filter:
                filter_expr = f'domain == "{domain_filter}"'

            # Perform search
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                expr=filter_expr,
                output_fields=["summary_id", "url", "domain", "created_at"]
            )

            # Format results
            formatted_results = []
            for hit in results[0]:  # results is a list of result sets
                formatted_results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'summary_id': hit.entity.get('summary_id'),
                    'url': hit.entity.get('url'),
                    'domain': hit.entity.get('domain'),
                    'created_at': hit.entity.get('created_at')
                })

            logger.info(f"Found {len(formatted_results)} similar documents")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            raise

    def delete_by_domain(self, domain: str) -> int:
        """
        Delete all embeddings for a specific domain.

        Args:
            domain: Domain to delete embeddings for

        Returns:
            Number of deleted embeddings
        """
        try:
            expr = f'domain == "{domain}"'
            result = self.collection.delete(expr)
            self.collection.flush()

            deleted_count = len(result.primary_keys) if result.primary_keys else 0
            logger.info(f"Deleted {deleted_count} embeddings for domain {domain}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting embeddings for domain {domain}: {str(e)}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            stats = {
                'collection_name': self.collection_name,
                'num_entities': self.collection.num_entities,
                'database_path': self.db_path
            }

            # Get index stats if available
            try:
                index_info = self.collection.indexes
                stats['index_info'] = str(index_info)
            except:
                stats['index_info'] = 'Not available'

            return stats

        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                'collection_name': self.collection_name,
                'num_entities': 0,
                'database_path': self.db_path,
                'error': str(e)
            }

    def optimize(self):
        """Optimize the database for better performance."""
        try:
            # Load collection into memory for faster searches
            self.collection.load()
            logger.info("Collection loaded into memory for optimization")

            # Build index if not exists
            if not self.collection.has_index():
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024}
                }
                self.collection.create_index("embedding", index_params)
                logger.info("Created index for optimization")

        except Exception as e:
            logger.error(f"Error optimizing database: {str(e)}")
            raise

    def close(self):
        """Close the database connection."""
        try:
            connections.disconnect(alias="default")
            logger.info("Disconnected from Milvus Lite")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus Lite: {str(e)}")


# Global instance for easy access
_milvus_service = None

def get_milvus_service() -> MilvusService:
    """Get or create global Milvus service instance."""
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService()
    return _milvus_service
