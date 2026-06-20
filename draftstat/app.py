import os

from fastapi import FastAPI

from draftstat.ui import attach

app = FastAPI(title="DraftStat")


@app.get("/health")
def health():
    return {"status": "ok"}


app = attach(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 7860)),
    )
