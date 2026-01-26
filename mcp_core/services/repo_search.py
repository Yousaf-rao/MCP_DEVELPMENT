import os
import shutil
import subprocess
import logging
import chromadb
from chromadb.utils import embedding_functions
from mcp_core.constants import IGNORE_DIRS

logger = logging.getLogger(__name__)

# Config
DB_PATH = "./chroma_db"
COLLECTION_NAME = "repo_files"
LOCAL_WORKSPACE = "./temp_workspace" # Where we clone the repo

class RepoSearch:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )

    def _run_git_command(self, args, cwd=None):
        """Helper to run git commands safely."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Git Error: {e.stderr}")
            raise Exception(f"Git command failed: {e.stderr}")

    def sync_from_remote(self, repo_url: str, branch: str = "main"):
        """
        Clones or Pulls the latest code from a remote Git repository into a local workspace.
        """
        # 1. Check if we already cloned it
        if os.path.exists(os.path.join(LOCAL_WORKSPACE, ".git")):
            logger.info(f"🔄 Repo exists. Pulling latest changes from {branch}...")
            # We don't error if fetch fails (e.g. no network), we just warn
            try:
                self._run_git_command(["fetch", "origin"], cwd=LOCAL_WORKSPACE)
                self._run_git_command(["reset", "--hard", f"origin/{branch}"], cwd=LOCAL_WORKSPACE)
            except Exception as e:
                logger.warning(f"⚠️ Git Pull failed: {e}. Using cached copy.")
        else:
            # 2. Fresh Clone
            if os.path.exists(LOCAL_WORKSPACE):
                # If dir exists but no .git, it's garbage. Clean it.
                shutil.rmtree(LOCAL_WORKSPACE) 
            
            logger.info(f"📥 Cloning {repo_url} ({branch})...")
            # Create dir if not makes sense, but clone creates it usually if we don't pass .
            # Here we are passing LOCAL_WORKSPACE as the target dir
            self._run_git_command(["clone", "-b", branch, repo_url, LOCAL_WORKSPACE])

        logger.info("✅ Codebase synced successfully.")

    def index_repo(self, sub_dir: str = ""):
        """
        Indexes the files inside the LOCAL_WORKSPACE.
        sub_dir: Optional subfolder (e.g., 'src') to limit scope.
        """
        # Determine where to start walking
        if not os.path.exists(LOCAL_WORKSPACE):
            logger.error(f"❌ Workspace not found at {LOCAL_WORKSPACE}. Did you sync?")
            return

        start_path = os.path.join(LOCAL_WORKSPACE, sub_dir)
        
        if not os.path.exists(start_path):
            logger.error(f"❌ Target directory not found: {start_path}")
            return

        file_paths = []
        ids = []
        documents = []

        # Use shared IGNORE_DIRS from constants (plus extras for indexing)
        ignored = IGNORE_DIRS | {"coverage", "__pycache__", ".vscode", "public"}

        logger.info(f"📚 Scanning files in: {start_path}")

        for root, dirs, files in os.walk(start_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignored]

            for file in files:
                if file.endswith((".tsx", ".ts", ".js", ".jsx", ".css", ".py", ".md")):
                    full_path = os.path.join(root, file)
                    
                    # CRITICAL: We want the ID to be the "Relative Path" (e.g., src/App.tsx)
                    # not the full temp path (./temp_workspace/src/App.tsx)
                    # This ensures the LLM sees clean paths.
                    rel_path = os.path.relpath(full_path, LOCAL_WORKSPACE)
                    
                    file_paths.append(full_path)
                    ids.append(rel_path)
                    documents.append(rel_path) # Searching by filename for now

        if not ids:
            logger.warning("⚠️ No files found to index!")
            return

        logger.info(f"📚 Indexing {len(ids)} files into Vector DB...")
        
        # Upsert into Chroma
        self.collection.upsert(
            documents=documents, # What we search against
            ids=ids,             # The unique key (Relative Path)
            metadatas=[{"fullpath": p} for p in file_paths] # Store real path logic if needed
        )
        logger.info("✅ Indexing Complete.")

    def search(self, query: str, limit: int = 10) -> list:
        """
        Returns relative paths (e.g. 'FigmaDesign/Header.jsx')
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            if results['ids']:
                return results['ids'][0] # Return the Relative Paths
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
