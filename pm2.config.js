module.exports = {
  apps: [
    {
      name: "asset-price-prediction-backend",
      script: "uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8000",
      interpreter: "python3",
      watch: false,
      env: {
        PYTHONPATH: "./app"
      }
    }
  ]
}
