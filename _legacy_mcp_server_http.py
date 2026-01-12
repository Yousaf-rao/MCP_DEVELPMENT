"""
Minimal MCP HTTP Transport for Sprint 1
- POST /mcp: JSON-RPC 2.0 (tools/list, tools/call)
- GET  /health: status
- Origin validation: ALLOWED_ORIGINS env (default localhost)
"""
import json
import os
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from pathlib import Path

from mcp_core import RepoToolsServer, ServerConfig, SearchConfig

ALLOWED_ORIGINS = set((os.getenv('ALLOWED_ORIGINS', 'http://localhost,http://127.0.0.1')).split(','))

config = ServerConfig(
    allowed_repos=["*"],
    allowed_roots=[Path.cwd() / 'sample-projects', Path.home() / 'Desktop', Path.cwd()]
)
search_config = SearchConfig()
repo_server = RepoToolsServer(config, search_config)

def set_security_headers(h: BaseHTTPRequestHandler):
    h.send_header('X-Content-Type-Options', 'nosniff')
    h.send_header('X-Frame-Options', 'DENY')
    h.send_header('Cache-Control', 'no-store')

class MCPHandler(BaseHTTPRequestHandler):
    def _check_origin(self):
        origin = self.headers.get('Origin')
        if origin and origin not in ALLOWED_ORIGINS:
            self.send_response(403)
            set_security_headers(self)
            self.end_headers()
            self.wfile.write(b'{"error":"Forbidden origin"}')
            return False
        return True
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            set_security_headers(self)
            self.end_headers()
            self.wfile.write(json.dumps({'status':'healthy','server':config.name,'version':config.version,'transport':'http'}).encode('utf-8'))
        else:
            self.send_response(404); set_security_headers(self); self.end_headers(); self.wfile.write(b'{"error":"Not found"}')
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/mcp':
            self.send_response(404); set_security_headers(self); self.end_headers(); self.wfile.write(b'{"error":"Not found"}')
            return
        if not self._check_origin():
            return
        length = int(self.headers.get('Content-Length','0'))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw.decode('utf-8'))
        except Exception:
            self.send_response(400); set_security_headers(self); self.end_headers(); self.wfile.write(b'{"error":"Invalid JSON"}')
            return
        jsonrpc = req.get('jsonrpc'); method = req.get('method'); req_id = req.get('id'); params = req.get('params', {})
        if jsonrpc != '2.0':
            self.send_response(400); set_security_headers(self); self.end_headers(); self.wfile.write(b'{"error":"jsonrpc must be 2.0"}')
            return
        if method == 'tools/list':
            tools = repo_server._tool_schemas()
            tool_dicts = [{'name':t.name,'description':t.description,'inputSchema':t.inputSchema} for t in tools]
            resp = {'jsonrpc':'2.0','id':req_id,'result':{'tools':tool_dicts}}
            self.send_response(200); self.send_header('Content-Type','application/json'); set_security_headers(self); self.end_headers(); self.wfile.write(json.dumps(resp).encode('utf-8'))
            return
        if method == 'tools/call':
            name = params.get('name'); arguments = params.get('arguments', {})
            try:
                # Dispatch to Modular Functions via server router
                # Using the router inside RepoToolsServer requires calling call_tool via the server instance
                # tailored for direct python calls if available, or reconstructing logic.
                # However, repo_server.server.call_tool is an async context manager normally used by stdio/SSE.
                # For this simple HTTP server, we manual dispatch as before OR we can adapt to use the new module structure.
                
                # RE-ADAPTING TO NEW MODULAR STRUCTURE for HTTP:
                # We can call the module functions directly or via the server instance if we expose a helper.
                # For now, let's use the direct module calls consistent with the previous version of this file
                # BUT updated to use the new asyncio.run pattern if they are async.
                
                if name == 'list_repo_files':
                    result_obj = asyncio.run(repo_server.ctx.filesystem.list_repo_files(repo_server.ctx, arguments)) # Wait, filesystem is a module, not on ctx
                    # Correct dispatch:
                    from mcp_core.tools import filesystem, git, figma
                    
                    if name == "list_repo_files":
                        result_obj = asyncio.run(filesystem.list_repo_files(repo_server.ctx, arguments))
                    elif name == "read_file":
                        result_obj = asyncio.run(filesystem.read_file(repo_server.ctx, arguments))
                    elif name == "locate_component":
                        result_obj = asyncio.run(filesystem.locate_component(repo_server.ctx, arguments))
                    elif name == "search_content":
                        result_obj = asyncio.run(filesystem.search_content(repo_server.ctx, arguments))
                    elif name == "create_branch":
                        result_obj = asyncio.run(git.create_branch(repo_server.ctx, arguments))
                    elif name == "fetch_figma_pattern":
                        result_obj = asyncio.run(figma.fetch_figma_pattern(repo_server.ctx, arguments))
                    elif name == "generate_react_code":
                        result_obj = asyncio.run(figma.generate_react_code(repo_server.ctx, arguments))
                    elif name == "save_code_file":
                        result_obj = asyncio.run(filesystem.save_code_file(repo_server.ctx, arguments))
                    elif name == "list_pending_events":
                        result_obj = asyncio.run(figma.list_pending_events(repo_server.ctx, arguments))
                    elif name == "mark_event_processed":
                        result_obj = asyncio.run(figma.mark_event_processed(repo_server.ctx, arguments))
                    else:
                         raise ValueError(f'Unknown tool: {name}')

                content = [{'type':'text','text':json.dumps(result_obj)}]
                resp = {'jsonrpc':'2.0','id':req_id,'result':{'content':content}}
                self.send_response(200); self.send_header('Content-Type','application/json'); set_security_headers(self); self.end_headers(); self.wfile.write(json.dumps(resp).encode('utf-8'))
            except Exception as e:
                err = {'jsonrpc':'2.0','id':req_id,'error':{'code':-32000,'message':str(e)}}
                self.send_response(500); set_security_headers(self); self.end_headers(); self.wfile.write(json.dumps(err).encode('utf-8'))
            return
        self.send_response(400); set_security_headers(self); self.end_headers(); self.wfile.write(b'{"error":"Unknown method"}')

def run(host='127.0.0.1', port=8080):
    httpd = HTTPServer((host, port), MCPHandler)
    print(f"HTTP MCP Server on http://{host}:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
