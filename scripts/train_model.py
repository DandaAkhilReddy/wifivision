#!/usr/bin/env python3
"""
Activity Classification Model Training Script

Trains a Random Forest classifier on labeled CSI data.

Expected data directory structure:
    data/labeled/
        no_presence/
            recording1.csv
            recording2.csv
        static_presence/
            recording1.csv
        small_movement/
            recording1.csv
        large_movement/
            recording1.csv

Usage:
    python train_model.py --data data/labeled --output models/activity_classifier.pkl
"""

import sys
import os
import argparse
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from parser import CSIParser
from detector import ActivityClassifier, CSIPreprocessor, create_windows


def load_labeled_data(data_dir: str, window_size: int = 100, stride: int = 50):
    """
    Load and prepare labeled training data.

    Args:
        data_dir: Path to labeled data directory
        window_size: Frames per window
        stride: Step between windows

    Returns:
        Tuple of (X_windows, y_labels)
    """
    X_windows = []
    y_labels = []

    preprocessor = CSIPreprocessor()
    csi_parser = CSIParser()

    for label in ActivityClassifier.CLASSES:
        label_dir = os.path.join(data_dir, label)

        if not os.path.exists(label_dir):
            print(f"Warning: Directory not found: {label_dir}")
            continue

        csv_files = [f for f in os.listdir(label_dir) if f.endswith('.csv')]

        if not csv_files:
            print(f"Warning: No CSV files in {label_dir}")
            continue

        print(f"\nLoading '{label}' data:")

        for filename in csv_files:
            filepath = os.path.join(label_dir, filename)
            print(f"  - {filename}...", end='')

            try:
                frames = csi_parser.load_file(filepath)
                amplitudes = csi_parser.get_amplitudes()

                if len(amplitudes) == 0:
                    print(" (no valid data)")
                    continue

                # Preprocess
                amplitudes = preprocessor.preprocess(amplitudes)

                # Create windows
                windows = create_windows(amplitudes, window_size, stride)

                X_windows.extend(windows)
                y_labels.extend([label] * len(windows))

                print(f" {len(windows)} windows")

            except Exception as e:
                print(f" ERROR: {e}")

    return X_windows, y_labels


def main():
    parser = argparse.ArgumentParser(
        description='Train activity classification model'
    )
    parser.add_argument(
        '--data', '-d',
        required=True,
        help='Path to labeled data directory'
    )
    parser.add_argument(
        '--output', '-o',
        default='models/activity_classifier.pkl',
        help='Output model path (default: models/activity_classifier.pkl)'
    )
    parser.add_argument(
        '--window-size',
        type=int,
        default=100,
        help='Frames per window (default: 100)'
    )
    parser.add_argument(
        '--stride',
        type=int,
        default=50,
        help='Step between windows (default: 50)'
    )
    parser.add_argument(
        '--test-split',
        type=float,
        default=0.2,
        help='Test set fraction (default: 0.2)'
    )
    parser.add_argument(
        '--cv-folds',
        type=int,
        default=5,
        help='Cross-validation folds (default: 5)'
    )

    args = parser.parse_args()

    print("WiFiVision Activity Classifier Training")
    print("=" * 50)

    # Load data
    print(f"\nLoading data from: {args.data}")
    X_windows, y_labels = load_labeled_data(
        args.data,
        window_size=args.window_size,
        stride=args.stride
    )

    if len(X_windows) == 0:
        print("\nNo training data found!")
        print("\nExpected directory structure:")
        for label in ActivityClassifier.CLASSES:
            print(f"  {args.data}/{label}/recording1.csv")
        sys.exit(1)

    print(f"\nTotal samples: {len(X_windows)}")

    # Class distribution
    unique, counts = np.unique(y_labels, return_counts=True)
    print("\nClass distribution:")
    for label, count in zip(unique, counts):
        print(f"  {label}: {count} ({100 * count / len(y_labels):.1f}%)")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_windows, y_labels,
        test_size=args.test_split,
        random_state=42,
        stratify=y_labels
    )

    print(f"\nTraining set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    # Train model
    print("\nTraining Random Forest classifier...")
    classifier = ActivityClassifier()
    classifier.train(X_train, y_train)

    # Cross-validation
    print(f"\n{args.cv_folds}-fold cross-validation...")
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import make_pipeline

    # Extract features for CV
    features_train = np.array([
        classifier.feature_extractor.extract_features(w) for w in X_train
    ])
    features_scaled = classifier.scaler.transform(features_train)

    cv_scores = cross_val_score(
        classifier.model,
        features_scaled,
        y_train,
        cv=args.cv_folds
    )
    print(f"CV Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")

    # Test set evaluation
    print("\nTest set evaluation:")
    y_pred = []
    for window in X_test:
        pred, _ = classifier.predict(window)
        y_pred.append(pred)

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred, labels=ActivityClassifier.CLASSES)
    print(f"{'':15}", end='')
    for label in ActivityClassifier.CLASSES:
        print(f"{label[:10]:>12}", end='')
    print()
    for i, label in enumerate(ActivityClassifier.CLASSES):
        print(f"{label:15}", end='')
        for j in range(len(ActivityClassifier.CLASSES)):
            print(f"{cm[i, j]:12}", end='')
        print()

    # Feature importance
    print("\nFeature Importance:")
    feature_names = classifier.feature_extractor.get_feature_names()
    importances = classifier.model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for idx in sorted_idx[:5]:
        print(f"  {feature_names[idx]}: {importances[idx]:.3f}")

    # Save model
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    classifier.save(args.output)
    print(f"\nModel saved to: {args.output}")


if __name__ == '__main__':
    main()
