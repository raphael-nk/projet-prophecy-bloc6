FROM python:3.12-slim

WORKDIR /app/api

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/main.py ./main.py
COPY api/routers ./routers
COPY api/services ./services
COPY train/reassort/predict.py /app/train/reassort/predict.py

ENV MODELS_DIR=/app/models
ENV DATA_DIR=/app/data
ENV TRAIN_DIR=/app/train
ENV MODEL_REASSORT=/app/models/xgboost_30d_final.pkl
ENV MODEL_SEGMENTATION=/app/models/kmeans_bundle_v1.joblib
ENV RFM_SEGMENTS_CSV=/app/data/rfm_segments.csv
ENV CUSTOMER_RECOMMENDATION_CSV=/app/data/customer_recommendation.csv

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
