from fastapi import FastAPI

from interfaces.api.routes.rag import router as rag_router

app = FastAPI()


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Hello, World!"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


app.include_router(rag_router)
