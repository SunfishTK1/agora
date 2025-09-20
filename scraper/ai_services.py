"""
AI services for text processing, summarization, and embeddings.
Enterprise-grade implementation with Azure OpenAI and OpenAI APIs.
"""

import os
import time
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import tiktoken

from openai import AzureOpenAI, OpenAI
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """
    Service for Azure OpenAI GPT-5 chat completions with intelligent text chunking.
    Handles large documents by splitting them into manageable chunks.
    """

    def __init__(self):
        # Azure OpenAI configuration
        self.azure_client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION or "2024-02-01",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.model_name = settings.AZURE_OPENAI_MODEL or "gpt-5-chat"

        # Token limits
        self.max_context_tokens = 120000  # Conservative limit for GPT-5
        self.max_output_tokens = 8000     # Conservative limit for dense summaries
        self.chunk_overlap_tokens = 200   # Overlap between chunks

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")  # Use GPT-4 tokenizer as approximation
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def generate_summary(self, text: str, url: str = "", title: str = "") -> Dict[str, Any]:
        """
        Generate a dense, information-rich summary optimized for embedding.

        Args:
            text: The text content to summarize
            url: URL of the page (for context)
            title: Page title (for context)

        Returns:
            Dictionary containing summary and metadata
        """
        start_time = time.time()

        try:
            # Count tokens in input text
            input_tokens = self._count_tokens(text)
            logger.info(f"Processing text with {input_tokens} tokens from {url}")

            # If text is small enough, process directly
            if input_tokens <= self.max_context_tokens:
                chunks = [text]
                chunk_count = 1
            else:
                # Split into chunks intelligently
                chunks = self._split_text_intelligently(text)
                chunk_count = len(chunks)

            # Process each chunk and combine results
            summary_parts = []
            total_input_tokens = 0
            total_output_tokens = 0

            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{chunk_count}")

                chunk_summary = self._summarize_chunk(chunk, url, title, i, chunk_count)
                summary_parts.append(chunk_summary['summary'])
                total_input_tokens += chunk_summary['input_tokens']
                total_output_tokens += chunk_summary['output_tokens']

            # Combine chunk summaries into final summary
            final_summary = self._combine_summaries(summary_parts, url, title)

            # Calculate metrics
            processing_time_ms = int((time.time() - start_time) * 1000)
            compression_ratio = len(text) / len(final_summary) if final_summary else 1.0

            return {
                'summary_text': final_summary,
                'summary_length_tokens': self._count_tokens(final_summary),
                'chunk_count': chunk_count,
                'processing_time_ms': processing_time_ms,
                'compression_ratio': compression_ratio,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'model_used': self.model_name
            }

        except Exception as e:
            logger.error(f"Error generating summary for {url}: {str(e)}")
            raise

    def _split_text_intelligently(self, text: str) -> List[str]:
        """Split text into chunks that preserve semantic meaning."""
        tokens = self.tokenizer.encode(text)
        chunks = []
        chunk_size = self.max_context_tokens - 2000  # Leave room for instructions

        for i in range(0, len(tokens), chunk_size - self.chunk_overlap_tokens):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)

        return chunks

    def _summarize_chunk(self, chunk: str, url: str, title: str, chunk_idx: int, total_chunks: int) -> Dict[str, Any]:
        """Summarize a single chunk of text."""
        system_prompt = """You are an expert at creating dense, information-rich summaries optimized for text embeddings.

Your task is to create a summary that:
1. Captures ALL critical information, facts, data, and insights
2. Preserves technical terms, proper nouns, and specific details
3. Maintains logical structure and relationships
4. Is written in a dense, compact style
5. Focuses on information that would be valuable for semantic search and retrieval

Guidelines:
- Be extremely thorough - include every important detail
- Use precise, specific language
- Maintain factual accuracy
- Preserve context and relationships between concepts
- Write economically but comprehensively"""

        user_prompt = f"""Create a dense, information-rich summary of the following text chunk {chunk_idx + 1} of {total_chunks}.

{text if not url else f"Source: {url}"}
{text if not title else f"Title: {title}"}

TEXT TO SUMMARIZE:
{chunk}

Please provide a summary that captures all essential information in a dense, compact format optimized for embedding and retrieval."""

        try:
            response = self.azure_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_output_tokens,
                temperature=0.3,  # Lower temperature for more focused summaries
                top_p=0.9,
                presence_penalty=0.0,
                frequency_penalty=0.0
            )

            summary = response.choices[0].message.content.strip()
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            return {
                'summary': summary,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens
            }

        except Exception as e:
            logger.error(f"Error in chunk summarization: {str(e)}")
            raise

    def _combine_summaries(self, summary_parts: List[str], url: str, title: str) -> str:
        """Combine multiple chunk summaries into a final coherent summary."""
        if len(summary_parts) == 1:
            return summary_parts[0]

        # Combine summaries with intelligent merging
        combined_text = "\n\n".join(summary_parts)

        # If combined text is still within limits, return as-is
        if self._count_tokens(combined_text) <= self.max_output_tokens:
            return combined_text

        # Otherwise, create a final summary of summaries
        system_prompt = """You are an expert at synthesizing multiple summaries into a single, coherent, dense summary.

Create a final summary that combines all the information from the provided summaries while maintaining:
- All critical facts, data, and insights
- Logical structure and relationships
- Dense, compact writing style
- Maximum information density"""

        user_prompt = f"""Synthesize these {len(summary_parts)} partial summaries into a single, dense, information-rich summary.

{text if not url else f"Source: {url}"}
{text if not title else f"Title: {title}"}

PARTIAL SUMMARIES:
{combined_text}

Provide a final summary that captures all essential information in a dense format."""

        try:
            response = self.azure_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_output_tokens,
                temperature=0.2,
                top_p=0.9
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error combining summaries: {str(e)}")
            # Fallback: return concatenated summaries
            return combined_text[:self.max_output_tokens * 4]  # Approximate character limit

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        try:
            return len(self.tokenizer.encode(text))
        except:
            # Fallback: rough approximation (1 token ≈ 4 characters)
            return len(text) // 4


class AzureOpenAIEmbeddingService:
    """
    Service for generating text embeddings using Azure OpenAI's text-embedding-large-3 model.
    Optimized for high-throughput batch processing with fallback to OpenAI.
    """

    def __init__(self):
        # Try Azure OpenAI first
        self.use_azure = self._setup_azure_client()
        
        # Fallback to OpenAI if Azure not available
        if not self.use_azure:
            logger.warning("Azure OpenAI embedding service not available, falling back to OpenAI")
            self._setup_openai_client()
        
        self.model_name = "text-embedding-large-3"
        self.dimensions = 3072  # text-embedding-large-3 dimensions

    def _setup_azure_client(self) -> bool:
        """Setup Azure OpenAI client for embeddings."""
        try:
            azure_key = getattr(settings, 'AZURE_OPENAI_EMBEDDING_API_KEY', None)
            azure_endpoint = getattr(settings, 'AZURE_OPENAI_EMBEDDING_ENDPOINT', None)
            azure_version = getattr(settings, 'AZURE_OPENAI_EMBEDDING_API_VERSION', '2024-02-01')
            azure_model = getattr(settings, 'AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-large-3')
            
            if azure_key and azure_endpoint:
                self.azure_client = AzureOpenAI(
                    api_key=azure_key,
                    api_version=azure_version,
                    azure_endpoint=azure_endpoint
                )
                self.azure_model_name = azure_model
                logger.info("Azure OpenAI embedding service initialized successfully")
                return True
            else:
                logger.info("Azure OpenAI embedding configuration not found")
                return False
        except Exception as e:
            logger.error(f"Failed to setup Azure OpenAI embedding client: {str(e)}")
            return False

    def _setup_openai_client(self):
        """Setup OpenAI client as fallback."""
        try:
            openai_key = getattr(settings, 'OPENAI_API_KEY', None)
            if openai_key:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("OpenAI embedding service initialized as fallback")
            else:
                raise ValueError("No OpenAI API key available for fallback")
        except Exception as e:
            logger.error(f"Failed to setup OpenAI embedding client: {str(e)}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            List of float values representing the embedding vector
        """
        try:
            if self.use_azure:
                response = self.azure_client.embeddings.create(
                    input=text,
                    model=self.azure_model_name,
                    dimensions=self.dimensions
                )
            else:
                response = self.openai_client.embeddings.create(
                    input=text,
                    model=self.model_name,
                    dimensions=self.dimensions
                )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # If Azure fails, try OpenAI fallback
            if self.use_azure and hasattr(self, 'openai_client'):
                logger.warning("Azure embedding failed, trying OpenAI fallback")
                try:
                    response = self.openai_client.embeddings.create(
                        input=text,
                        model=self.model_name,
                        dimensions=self.dimensions
                    )
                    return response.data[0].embedding
                except Exception as fallback_error:
                    logger.error(f"OpenAI fallback also failed: {str(fallback_error)}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            # Azure OpenAI and OpenAI have limits of ~2048 inputs per batch
            batch_size = 2048
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.info(f"Processing embedding batch {i//batch_size + 1}: {len(batch)} texts")

                if self.use_azure:
                    response = self.azure_client.embeddings.create(
                        input=batch,
                        model=self.azure_model_name,
                        dimensions=self.dimensions
                    )
                else:
                    response = self.openai_client.embeddings.create(
                        input=batch,
                        model=self.model_name,
                        dimensions=self.dimensions
                    )

                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)

            return all_embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            # If Azure fails, try OpenAI fallback for the current batch
            if self.use_azure and hasattr(self, 'openai_client'):
                logger.warning("Azure batch embedding failed, trying OpenAI fallback")
                try:
                    # Retry with smaller batches for safety
                    batch_size = 1024
                    all_embeddings = []
                    
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i:i + batch_size]
                        response = self.openai_client.embeddings.create(
                            input=batch,
                            model=self.model_name,
                            dimensions=self.dimensions
                        )
                        batch_embeddings = [data.embedding for data in response.data]
                        all_embeddings.extend(batch_embeddings)
                    
                    return all_embeddings
                except Exception as fallback_error:
                    logger.error(f"OpenAI fallback batch also failed: {str(fallback_error)}")
            raise


# Alias for backward compatibility
OpenAIEmbeddingService = AzureOpenAIEmbeddingService
