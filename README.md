# 🌍 Global Air Pollution Analysis & AQI Prediction

An end-to-end machine learning project that analyses global air-quality data,
engineers advanced pollutant features, trains ensemble models (Random Forest +
XGBoost) for both **AQI regression** and **AQI-category classification**, and
exposes predictions through a FastAPI service.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train models (downloads data automatically via Kaggle API)
python main.py --mode train

# 3. Evaluate & generate all plots / SHAP explanations
python main.py --mode evaluate

# 4. Start the prediction API
python main.py --mode serve

# 5. Or run everything end-to-end
python main.py --mode all
```

## Project Structure

```
air_pollution_ml/
├── data/                        # Raw and processed data
├── models/                      # Saved model files
├── plots/                       # All output visualizations
├── logs/                        # Pipeline logs
├── notebooks/
│   └── exploration.ipynb        # Optional EDA notebook
├── src/
│   ├── __init__.py
│   ├── data_loader.py           # Dataset download + loading
│   ├── feature_engineering.py   # All feature creation
│   ├── train.py                 # Model training pipeline
│   ├── evaluate.py              # Metrics + explainability
│   └── inference.py             # FastAPI prediction endpoint
├── tests/                       # pytest test suite
├── requirements.txt
├── README.md
└── main.py                      # Master runner script
```

## Models

| Model | Task | Scoring |
|-------|------|---------|
| Random Forest Regressor | AQI value prediction | MAE |
| XGBoost Regressor | AQI value prediction | MAE |
| Random Forest Classifier | AQI category prediction | F1 weighted |
| XGBoost Classifier | AQI category prediction | F1 weighted |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/predict/regression` | Predict AQI value |
| `POST` | `/predict/classification` | Predict AQI category |
| `GET`  | `/health` | Health check |

## Dataset

[Global Air Pollution Dataset](https://www.kaggle.com/datasets/sazidthe1/global-air-pollution-data) from Kaggle.

Place `global_air_pollution_data.csv` in the `data/` folder, or ensure your
Kaggle API credentials are configured and the CLI will download it
automatically.

## Testing

```bash
pytest tests/ -v
```

## License

MIT
