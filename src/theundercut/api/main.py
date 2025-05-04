from fastapi import FastAPI

app = FastAPI(title="The Undercut – API")

@app.get("/healthz")
async def health():
    return {"ok": True}
