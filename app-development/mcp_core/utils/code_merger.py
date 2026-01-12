import re
from typing import Tuple, Dict
from .style_merger import StyleMerger

class CodeMerger:
    START_MARKER = r"\{\/\* @mcp-begin:view \*\/\}"
    END_MARKER = r"\{\/\* @mcp-end:view \*\/\}"
    
    @staticmethod
    def merge(existing_code: str, new_code: str) -> str:
        """
        Phase 12 Soft Fallback:
        1. SCOPE DETECTION: Determines if we are merging a specific 'View Zone' or the whole file.
        2. RECONCILIATION: Always attempts to map IDs -> Classes, regardless of scope.
        """
        
        # --- 1. SCOPE DETECTION ---
        
        # Analyze Existing Code
        existing_match = re.search(f"({CodeMerger.START_MARKER})(.*?)({CodeMerger.END_MARKER})", existing_code, re.DOTALL)
        
        if existing_match:
            # Case A: Markers Found (Standard Logic)
            # We only care about the content INSIDE the markers.
            pre_content = existing_code[:existing_match.start()]
            scope_content = existing_match.group(2)
            post_content = existing_code[existing_match.end():]
            has_markers = True
        else:
            # Case B: Markers Missing (Soft Fallback)
            # We treat the ENTIRE file as the scope to salvage edits.
            pre_content = ""
            scope_content = existing_code
            post_content = ""
            has_markers = False

        # Analyze New Code (to extract the corresponding update)
        new_match = re.search(f"({CodeMerger.START_MARKER})(.*?)({CodeMerger.END_MARKER})", new_code, re.DOTALL)
        
        if new_match:
            # If generator honored markers, use the inner content
            new_inner_content = new_match.group(2)
            
            if has_markers:
                # Standard: Replace Inner with Inner
                target_new_content = new_inner_content
            else:
                # Soft Fallback: Replace Full File with Full New File (but keep styles)
                # If existing had no markers but new does, we use the whole new file structure
                target_new_content = new_code
        else:
            # Generator didn't output markers (or simple file)
            target_new_content = new_code

        # --- 2. RECONCILIATION (The "Salvage" Step) ---
        
        # A. Extract ID Map from the scoped old content
        id_class_map = CodeMerger._extract_id_map(scope_content)
        
        # B. Patch the new content using that map
        patched_content = CodeMerger._patch_content(target_new_content, id_class_map)
        
        # --- 3. ASSEMBLY ---
        
        if has_markers:
            # Reconstruct: Old Top + Marker + Patched View + Marker + Old Bottom
            start_tag = existing_match.group(1) 
            end_tag = existing_match.group(3)
            return pre_content + start_tag + patched_content + end_tag + post_content
        else:
            # Soft Fallback: Return the full patched file
            return patched_content

    @staticmethod
    def _extract_id_map(content: str) -> Dict[str, str]:
        """
        Scans content for data-mcp-id and extracts associated className.
        """
        id_class_map = {}
        # Simple heuristic: Split by tag closures to isolate elements roughly
        tags = content.split(">")
        
        for tag in tags:
            # Look for ID
            id_match = re.search(r'data-mcp-id="([^"]+)"', tag)
            if id_match:
                node_id = id_match.group(1)
                # Look for Class in the same tag fragment
                class_match = re.search(r'className="([^"]+)"', tag)
                if class_match:
                    id_class_map[node_id] = class_match.group(1)
        
        return id_class_map

    @staticmethod
    def _patch_content(content: str, id_map: Dict[str, str]) -> str:
        """
        Replaces classNames in content based on the id_map using StyleMerger.
        """
        def replace_callback(match):
            tag_content = match.group(0)
            
            # 1. Identify ID
            id_m = re.search(r'data-mcp-id="([^"]+)"', tag_content)
            if not id_m: return tag_content
            
            node_id = id_m.group(1)
            
            # 2. Check if we have preserved styles for this ID
            if node_id not in id_map:
                return tag_content
                
            old_classes = id_map[node_id]
            
            # 3. Find new classes
            class_m = re.search(r'className="([^"]+)"', tag_content)
            new_classes = class_m.group(1) if class_m else ""
            
            # 4. Merge
            merged_classes = StyleMerger.reconcile_classes(old_classes, new_classes)
            
            # 5. Inject back into string
            if class_m:
                return tag_content.replace(f'className="{new_classes}"', f'className="{merged_classes}"')
            else:
                # Inject className before ID if it didn't exist
                return tag_content.replace(f'data-mcp-id="{node_id}"', f'className="{merged_classes}" data-mcp-id="{node_id}"')

        # Regex matches any opening tag containing a data-mcp-id
        # Safe regex to match opening tags with attributes
        return re.sub(r'<[\w]+[^>]*data-mcp-id="[^"]+"[^>]*>', replace_callback, content)
