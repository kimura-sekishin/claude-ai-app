from fastapi import FastAPI

app = FastAPI(title="claude-code-python", version="0.1.0")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items/{item_id}")
async def get_item(item_id: int, name: str | None = None) -> dict[str, object]:
    return {"item_id": item_id, "name": name}
