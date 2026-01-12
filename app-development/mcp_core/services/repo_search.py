import os
import chromadb
import logging
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Config
DB_PATH = "./chroma_db"
COLLECTION_NAME = "repo_files"

class RepoSearch:
    def __init__(self):
        # Initialize persistent client (saves to disk)
        self.client = chromadb.PersistentClient(path=DB_PATH)
        
        # Use default embedding model (all-MiniLM-L6-v2)
        # This converts "LoginScreen" into vector numbers
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )

    def index_repo(self, root_dir: str = "src"):
        """
        Scans your project and saves all file paths to the Vector DB.
        Call this on startup.
        """
        file_paths = []
        ids = []
        
        # IGNORE LIST
        IGNORED_DIRS = {
            "node_modules", ".git", ".next", "dist", "build", 
            "coverage", "__pycache__", ".vscode", "public"
        }

        # 1. Walk the directory
        for root, dirs, files in os.walk(root_dir):
            # MODIFY 'dirs' IN-PLACE to prevent walking into ignored folders
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            for file in files:
                # Filter for code files only
                if file.endswith((".tsx", ".ts", ".js", ".jsx", ".css", ".py", ".md")):
                    # Optional: Skip test files to avoid confusing the router
                    if ".test." in file or ".spec." in file:
                        continue
                        
                    path = os.path.join(root, file)
                    file_paths.append(path)
                    ids.append(path) # Use path as the unique ID

        if not file_paths:
            logger.warning(f"⚠️ No files found to index in {root_dir}!")
            return

        logger.info(f"📚 Indexing {len(file_paths)} files from {root_dir} into Vector DB...")
        
        # 2. Add to ChromaDB (Upsert handles updates/duplicates)
        self.collection.upsert(
            documents=file_paths,
            ids=ids
        )
        logger.info("✅ Indexing Complete.")

    def search(self, query: str, limit: int = 10) -> list:
        """
        Returns the top 'limit' most relevant file paths for the given query.
        Example: Query "User Settings" -> ["src/pages/Settings.tsx", ...]
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            # Chroma returns a list of lists, we just need the first list of documents
            if results['documents']:
                return results['documents'][0]
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
