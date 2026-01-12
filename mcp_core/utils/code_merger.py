import re
from typing import Tuple
from .style_merger import StyleMerger

class CodeMerger:
    START_MARKER = r"\{\/\* @mcp-begin:view \*\/\}"
    END_MARKER = r"\{\/\* @mcp-end:view \*\/\}"
    
    @staticmethod
    def merge(existing_code: str, new_code: str) -> str:
        """
        Merge new_code into existing_code using Zone Markers.
        If markers are found in existing_code, replace the content between them
        with the content between markers in new_code.
        If no markers in existing_code, return new_code (overwrite) or heuristic (TODO).
        """
        
        # Check for markers in existing code
        existing_match = re.search(f"({CodeMerger.START_MARKER})(.*?)({CodeMerger.END_MARKER})", existing_code, re.DOTALL)
        
        if not existing_match:
            # Fallback: No markers in existing file -> Full Overwrite
            # In future: Heuristic AST matching for return() statement
            return new_code
            
        # Check for markers in new code (to extract the update)
        new_match = re.search(f"({CodeMerger.START_MARKER})(.*?)({CodeMerger.END_MARKER})", new_code, re.DOTALL)
        
        if not new_match:
            # New code wasn't generated with markers? This implies a configuration mismatch or error.
            # Return new_code to be safe (overwrite) or raise warning?
            # Let's assume overwrite if we can't find zone in input.
            return new_code
            
        # Perform replacement
        # We keep the markers in the final file to preserve the zone for next time.
        start_tag = existing_match.group(1)
        end_tag = existing_match.group(3)
        old_content = existing_match.group(2)
        new_content = new_match.group(2)
        
        # Semantic Reconciliation Step
        # 1. Build map of {id: className} from old_content
        # Regex: data-mcp-id="([^"]+)" text-maybe className="([^"]+)"
        # Note: Order of props varies. We scan for IDs, then look for className in the tag.
        # Simplification for MVP: Assume basic prop structure or scan tag blocks.
        # Let's use a robust strategy: Find all tags with data-mcp-id.
        

        
        # Find all tags in old content that have data-mcp-id
        # We capture the ID and the className if present
        # Pattern: <tag ... data-mcp-id="123" ... className="foo" ... >
        # This is hard with regex. 
        # Alternative: Just find pairs of (id, class) independently? No relation lost.
        # Strategy: Iterate through new_content tags. For each, grab its ID. Find that ID in old_content. Grab old className. Merge.
        
        def replace_classname(match):
            # match is the entire tag or the className prop? 
            # We need to match the whole tag to find the ID.
            # But python regex replace is per match.
            # Let's match the className attribute specifically, but we need context of ID.
            return match.group(0) # Placeholder
            
        # Better Strategy:
        # 1. Extract all ID->Class mappings from Old Content
        id_class_map = {}
        # Pattern: finds data-mcp-id="X" ... className="Y" OR className="Y" ... data-mcp-id="X"
        # We assume standard formatting from our generator: tag followed by props.
        # Let's scan for any string containing both.
        # Since we generated it, we know `className` comes before `data-mcp-id` typically? verification required.
        # In figma.py: `props_list` appends className THEN id. So `className="..." ... data-mcp-id="..."`
        
        # Regex to capture id and class from a tag string is complex.
        # Let's use a simpler heuristic:
        # Find all `data-mcp-id="([^"]+)"`.
        # Search backwards for `className="([^"]+)"`? formatting reliant.
        
        # Let's try iterating new_content and patching.
        # We need to know what to put in.
        
        # Extract Old Ids/Classes
        # We will split old content by "<" to approximate tags.
        old_tags = old_content.split("<")
        for tag_str in old_tags:
            id_match = re.search(r'data-mcp-id="([^"]+)"', tag_str)
            class_match = re.search(r'className="([^"]+)"', tag_str)
            if id_match and class_match:
                id_class_map[id_match.group(1)] = class_match.group(1)
                
        # Patch New Content
        # We use a callback function for re.sub to inject merged classes
        def patch_tag(match):
            tag_content = match.group(0) # The full tag content
            # Check for ID
            id_m = re.search(r'data-mcp-id="([^"]+)"', tag_content)
            if not id_m:
                return tag_content
                
            node_id = id_m.group(1)
            if node_id not in id_class_map:
                return tag_content
                
            # If we have an ID match, we need to merge classes
            old_classes = id_class_map[node_id]
            
            # Find new classes
            class_m = re.search(r'className="([^"]+)"', tag_content)
            new_classes = class_m.group(1) if class_m else ""
            
            merged = StyleMerger.reconcile_classes(old_classes, new_classes)
            
            # Replace className in this tag
            if class_m:
                return tag_content.replace(f'className="{new_classes}"', f'className="{merged}"')
            else:
                # Add className if it was missing but now we have merged classes?
                # Usually new content has className="" defaulting.
                # If generated code didn't have className, we might need to insert it.
                # figma.py generates `className` if `class_name` variable has content.
                # If empty, it might be omitted?
                # Re-check figma.py: `if class_name: props_list.append...`
                # So if new design has no classes, we might miss the prop.
                # But we want to inject preserved classes!
                # Insert before data-mcp-id
                return tag_content.replace(f'data-mcp-id="{node_id}"', f'className="{merged}" data-mcp-id="{node_id}"')

        # Regex to match open tags: <[word] ... >
        # Be careful not to match too much. Non-greedy.
        # \s[^>]* matches attributes.
        new_content_patched = re.sub(r'<[\w]+[^>]*data-mcp-id="[^"]+"[^>]*>', patch_tag, new_content)
        
        pre = existing_code[:existing_match.start()]
        post = existing_code[existing_match.end()]
        
        return pre + start_tag + new_content_patched + end_tag + post
