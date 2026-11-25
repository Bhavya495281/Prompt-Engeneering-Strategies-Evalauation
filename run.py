import threading
import webbrowser
import uvicorn
PORT = 8000
if __name__ == "__main__":
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    print(f"Prompt Eval Lab running at http://localhost:{PORT}  (press Ctrl+C to stop)")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=PORT)
