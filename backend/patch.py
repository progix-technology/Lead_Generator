import traceback
import sys

original_handler = None

def patch_exception_handler():
    from app.core.exceptions import add_exception_handlers
    
    # We will just write a wrapper script that runs the server and injects middleware to catch exceptions
    pass
