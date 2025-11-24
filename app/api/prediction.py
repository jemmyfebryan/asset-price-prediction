from fastapi import APIRouter
from pydantic import BaseModel
# from app.services.predictor import predict_and_store_result

router = APIRouter(prefix="/prediction", tags=["Price Prediction"])


class PredictionRequest(BaseModel):
    asset_code: str
    timestamp: int
    interval: str  # e.g., 'hourly', 'daily', 'weekly'


@router.post("/predict")
def predict_price(req: PredictionRequest):
    """Predict price for given timestamp and asset code."""
    # result = predict_and_store_result(req.asset_code, req.timestamp, req.interval)
    return {"status": "completed", "result": "wow mempredik"}
