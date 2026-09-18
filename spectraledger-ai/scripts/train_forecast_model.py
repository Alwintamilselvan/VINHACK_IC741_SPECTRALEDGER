"""
CLI entry point to (re)train the forecasting model from the synthetic
telemetry CSV, printing a quick training-error summary.

Usage:
    python -m scripts.train_forecast_model
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.forecasting import train_model  # noqa: E402


def main():
    bundle = train_model()
    print(f"Trained model_version={bundle.model_version}")
    print(f"Trained at: {bundle.trained_at}")
    print(f"Train MAE (point model, Mbps): {bundle.train_mae:.2f}")
    print(f"Feature columns: {bundle.feature_columns}")


if __name__ == "__main__":
    main()
