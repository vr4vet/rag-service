
from abc import ABC, abstractmethod
from pymongo import MongoClient
import logging

from src.context import Context
from src.embeddings import similarity_search 
from src.config import (
    RAG_DATABASE_SYSTEM,
    MONGODB_URI,
    MONGODB_COLLECTION,
    MONGODB_DATABASE,
)


class Database(ABC):
    """
    Abstract class for Connecting to a Database
    """

    @classmethod
    def __instancecheck__(cls, instance: any) -> bool:
        return cls.__subclasscheck__(type(instance))

    @classmethod
    def __subclasscheck__(cls, subclass: any) -> bool:
        return (
            hasattr(subclass, "get_context") and callable(subclass.get_context)
        ) and (
            hasattr(subclass, "post_context") and callable(subclass.post_context)
        )
    
    @abstractmethod
    def get_context(self, 
        document_name: str, 
        embedding: list[float]
    ) -> list[Context]:
        """
        Get context from database

        Args:
            embedding (list[float])
            document_name (str)

        Returns:
            list[Context]: The context related to the question
        """
        pass
    
    @abstractmethod
    def post_context(
        self,
        text: str,
        document_name: str,
        NPC: int,
        embedding: list[float],
        id: str,
    ) -> bool:
        """
        Post the curriculum to the database

        Args:
            text (str): The text to be posted
            embedding (list[float]): The embedding

        Returns:
            bool: if the context was posted
        """
    
        pass
    
    @abstractmethod
    def is_reachable(self) -> bool:
        """
        Check if database is reachable

        Returns:
            bool: reachable
        """
        pass
    
    
    


class MongoDB(Database):
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DATABASE]
        self.collection = self.db[MONGODB_COLLECTION]
        self.similarity_threshold = 0.7

    def get_context(self, document_id: str, embedding: list[float]) -> list[Context]:
        if not embedding:
            raise ValueError("Embedding cannot be None")

        # Define the MongoDB query that utilizes the search index "embeddings".
        query = {
            "$vectorSearch": {
                "index": "embeddings",
                "path": "embedding",
                "queryVector": embedding,
                "numCandidates": 30, # numCandidates = 10 * limit
                "limit": 3,
            }
        }

        # Execute the query
        documents = self.collection.aggregate([query])

        if not documents:
            raise ValueError("No documents found")

        # Convert to list
        documents = list(documents)

        results = []

        # Filter out the documents with low similarity
        for document in documents:
            if document["documentId"] != document_id:
                continue

            if (
                similarity_search(embedding, document["embedding"])
                > self.similarity_threshold
            ):
                results.append(
                    Context(
                        text=document["text"],
                        document_name=document["documentName"],
                        NPC=document["NPC"],
                    )
                )

        return results

    def post_context(
        self,
        text: str,
        document_name: str,
        NPC: int,
        embedding: list[float],
        document_id: str,
    ) -> bool:
        if not text:
            raise ValueError("text cannot be None")
        
        if NPC is None:
            raise ValueError("NPC cannot be None")
        
        if not document_name:
            raise ValueError("Document name cannot be None")
        
        if not embedding:
            raise ValueError("Embedding cannot be None")

        try:
            # Insert the curriculum into the database with metadata
            self.collection.insert_one(
                {
                    "text": text,
                    "documentName": document_name,
                    "NPC": NPC,
                    "embedding": embedding,
                    "documentId": document_id,
                }
            )
            return True
        except:
            return False

    def is_reachable(self) -> bool:
        try:
            # Send a ping to confirm a successful connection
            self.client.admin.command("ping")
            logger.info("Successfully pinged MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to ping MongoDB: {e}")
            return False




class MockDatabase(Database):
    """
    A mock database for testing purposes, storing data in memory.
    Singleton implementation to ensure only one instance exists.
    """

    _instance = None  # Class variable to hold the singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # If no instance exists, create one
            cls._instance = super(MockDatabase, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Initialize only once (avoiding resetting on subsequent calls)
        if not hasattr(self, "initialized"):
            self.data = []  # In-memory storage for mock data
            self.similarity_threshold = 0.7
            self.initialized = True

    def get_curriculum(self, document_name: str, embedding: list[float]) -> list[Context]:
        if not embedding:
            raise ValueError("Embedding cannot be None")

        results = []

        # Filter documents based on similarity and document_name
        for document in self.data:
            if document["document_name"] == document_name:
                similarity = similarity_search(embedding, document["embedding"])
                if similarity > self.similarity_threshold:
                    results.append(
                        Context(
                            text=document["text"],
                            document_name=document["document_name"],
                            NPC=document["NPC"],
                        )
                    )
        return results 

    def post_curriculum(
        self,
        curriculum: str,
        page_num: int,
        predicted_page_number: int,
        document_name: str,
        embedding: list[float],
        document_id: str,
    ) -> bool:
        if not curriculum or not document_name or page_num is None or not embedding:
            raise ValueError("All parameters are required and must be valid")

        # Append a new document to the in-memory storage
        self.data.append(
            {
                "text": curriculum,
                "page_num": page_num,
                "predicted_page_number": predicted_page_number,
                "document_name": document_name,
                "embedding": embedding,
                "document_id": document_id,
            }
        )
        return True

    def is_reachable(self) -> bool:
        return True


def get_database() -> Database:
    """
    Get the database to use

    Returns:
        Database: The database to use
    """
    match RAG_DATABASE_SYSTEM.lower():
        case "mock":
            return MockDatabase()  # This will always return the singleton instance
        case "mongodb":
            return MongoDB()
        case _:
            raise ValueError("Invalid database type")
