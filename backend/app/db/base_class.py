import re
from typing import Any
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    id: Any
    __name__: str

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """
        Automatically generate table name from class name.
        Example: UserSession -> user_sessions, Category -> categories
        """
        name = cls.__name__
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        
        # Simple pluralization rule
        if snake.endswith('y'):
            return snake[:-1] + 'ies'
        elif snake.endswith('s'):
            return snake  # Already pluralized
        else:
            return snake + 's'
