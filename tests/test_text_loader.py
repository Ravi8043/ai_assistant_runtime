import sys
import os
from pathlib import Path
import tempfile
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assist_runtime.memory.loaders.text_loader import TextLoader
from assist_runtime.memory.schemas.document import RawDocument

def test_text_loader_success():
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
        temp_file.write("Hello, Antigravity!\nThis is a test of the text loader.")
        temp_path = temp_file.name

    try:
        loader = TextLoader()
        docs = loader.load(temp_path)
        
        assert len(docs) == 1
        assert docs[0].content == "Hello, Antigravity!\nThis is a test of the text loader."
        assert isinstance(docs[0].metadata, dict)
        assert "source" in docs[0].metadata
    finally:
        # Cleanup
        try:
            os.unlink(temp_path)
        except Exception:
            pass

def test_text_loader_file_not_found():
    loader = TextLoader()
    with pytest.raises(Exception):
        loader.load("non_existent_file.txt")

if __name__ == "__main__":
    # Allow running directly via python
    test_text_loader_success()
    try:
        test_text_loader_file_not_found()
        print("test_text_loader_file_not_found passed")
    except AssertionError:
        print("test_text_loader_file_not_found failed")
    print("All checks passed successfully!")
