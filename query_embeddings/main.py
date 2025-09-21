from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
from typing import List, Any
from pymilvus import Collection, connections


from contextlib import asynccontextmanager

app = FastAPI(lifespan=lifespan)

# Milvus connection settings (adjust as needed)
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "embeddings"
@asynccontextmanager
async def lifespan(app):
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    yield


class QueryRequest(BaseModel):
    query: str

class QueryResult(BaseModel):
    ids: List[Any]
    scores: List[float]
    payloads: List[Any]

def generate_embedding(query: str) -> list:
    return [0.0] * 768  


@app.post("/query_embeddings", response_model=QueryResult)
def query_embeddings(request: QueryRequest):
    dummy_embedding = generate_embedding(request.query)

    collection = Collection(COLLECTION_NAME)
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    results = collection.search(
        data=[dummy_embedding],
        anns_field="embedding",  # Adjust field name as needed
        param=search_params,
        limit=5,
        output_fields=["payload"]  # Adjust as needed
    )
    ids = []
    scores = []
    payloads = []
    for hit in results[0]:
        ids.append(hit.id)
        scores.append(hit.distance)
        payloads.append(hit.entity.get("payload", {}))
    return QueryResult(ids=ids, scores=scores, payloads=payloads)
                
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
