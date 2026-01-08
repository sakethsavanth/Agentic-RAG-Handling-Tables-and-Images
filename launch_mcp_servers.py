"""
MCP Servers Launcher
Launch all MCP servers (Webhook, Streaming API, Cohere) at once
"""
import subprocess
import sys
import time
from pathlib import Path

def launch_servers():
    """Launch all MCP servers"""
    
    print("\n" + "=" * 80)
    print("🚀 LAUNCHING MCP SERVERS")
    print("=" * 80 + "\n")
    
    # Use the same Python interpreter that's running this script
    # This ensures we use the venv if it's activated
    python_exe = sys.executable
    print(f"📍 Using Python: {python_exe}\n")
    
    project_root = Path(__file__).parent
    
    # Define servers to launch
    servers = [
        {
            "name": "Webhook Server",
            "script": "webhook_server.py",
            "port": 8080,
            "description": "Asynchronous document processing"
        },
        {
            "name": "Streaming API",
            "script": "streaming_api.py",
            "port": 8090,
            "description": "Real-time query processing with SSE"
        },
        {
            "name": "Cohere MCP",
            "script": "cohere_mcp.py",
            "port": 8100,
            "description": "Cohere reranking via MCP"
        }
    ]
    
    processes = []
    
    for server in servers:
        script_path = project_root / server["script"]
        
        if not script_path.exists():
            print(f"⚠️ Script not found: {server['script']}")
            continue
        
        print(f"🔧 Starting {server['name']}...")
        print(f"   Port: {server['port']}")
        print(f"   Description: {server['description']}")
        
        try:
            # Launch server in new process using the current Python interpreter
            # Note: Don't capture stdout/stderr - let servers write to console
            # Capturing output causes pipe buffer to fill up and servers to hang
            process = subprocess.Popen(
                [python_exe, str(script_path)],
                cwd=str(project_root),
                # Allow servers to write directly to console
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            processes.append({
                "name": server["name"],
                "process": process,
                "port": server["port"]
            })
            
            print(f"   ✅ Started (PID: {process.pid})")
            time.sleep(1)  # Give time to start
            
        except Exception as e:
            print(f"   ❌ Failed to start: {str(e)}")
    
    print("\n" + "=" * 80)
    print("✅ SERVER LAUNCH COMPLETE")
    print("=" * 80 + "\n")
    
    # Display status
    print("📡 Server Status:\n")
    for proc_info in processes:
        print(f"   {proc_info['name']}")
        print(f"   └─ http://localhost:{proc_info['port']}")
        print(f"      PID: {proc_info['process'].pid}")
        print()
    
    print("\n💡 To stop servers, press Ctrl+C or close this window\n")
    print("📊 Servers are running in separate console windows")
    print("   You can close this launcher window after verifying all servers started\n")
    
    # Keep script running and monitor server health
    try:
        print("🔍 Monitoring server processes...")
        while True:
            time.sleep(5)
            
            # Check if any process died unexpectedly
            dead_servers = []
            for proc_info in processes:
                retcode = proc_info["process"].poll()
                if retcode is not None:
                    print(f"⚠️ {proc_info['name']} has stopped (exit code: {retcode})")
                    dead_servers.append(proc_info)
            
            # Remove dead servers from list
            for dead in dead_servers:
                processes.remove(dead)
            
            if not processes:
                print("\n⚠️ All servers have stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down servers...")
        for proc_info in processes:
            print(f"   Stopping {proc_info['name']}...")
            proc_info["process"].terminate()
        
        print("\n✅ All servers stopped\n")


if __name__ == "__main__":
    launch_servers()
