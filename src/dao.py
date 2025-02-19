
from abc import ABC, abstractmethod
from context import Context

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
    def get_context(self, document_name: str, embedding: list[float]) -> list[Context]:
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
            embedding (list[float]): The embedding of the question

        Returns:
            bool: True if the curriculum was posted, False otherwise
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
    
    