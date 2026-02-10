"""
Logging utilities for DeterministicWalkers.

Provides a simple, consistent logging interface across all modules.
"""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.
    
    Args:
        name: Logger name, typically __name__ of the module
        
    Returns:
        Configured logger instance
        
    Example:
        >>> from generator.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.warning("Something went wrong")
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '[%(levelname)s] %(name)s: %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)  # Default to WARNING
    
    return logger


# Convenience function to set global log level
def set_log_level(level: str) -> None:
    """
    Set the log level for all DeterministicWalkers loggers.
    
    Args:
        level: One of 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
        
    Example:
        >>> from generator.logger import set_log_level
        >>> set_log_level('DEBUG')  # Show all debug messages
    """
    level_value = getattr(logging, level.upper(), logging.WARNING)
    logging.getLogger('generator').setLevel(level_value)
    logging.getLogger('judge').setLevel(level_value)
    logging.getLogger('qa').setLevel(level_value)
    logging.getLogger('tools').setLevel(level_value)
