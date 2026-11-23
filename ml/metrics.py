"""Measured evaluation only; unavailable ROC-AUC is represented as null."""
import numpy as np
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             precision_recall_fscore_support, roc_auc_score)


def classification_metrics(labels, probabilities, classes):
    probabilities = np.asarray(probabilities)
    predicted = probabilities.argmax(axis=1)
    indexes = list(range(len(classes)))
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predicted, labels=indexes, average="macro", zero_division=0)
    matrix = confusion_matrix(labels, predicted, labels=indexes)
    per_class = {}
    for i, name in enumerate(classes):
        tp, fn = int(matrix[i, i]), int(matrix[i].sum() - matrix[i, i])
        fp = int(matrix[:, i].sum() - tp)
        tn = int(matrix.sum() - tp - fn - fp)
        per_class[name] = {"sensitivity": tp / (tp + fn) if tp + fn else None,
                           "specificity": tn / (tn + fp) if tn + fp else None, "support": tp + fn}
    try:
        auc = roc_auc_score(labels, probabilities[:, 1]) if len(classes) == 2 else roc_auc_score(labels, probabilities, multi_class="ovr", labels=indexes)
    except ValueError:
        auc = None
    return {"accuracy": float(accuracy_score(labels, predicted)), "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
            "macro_precision": float(precision), "macro_recall": float(recall), "macro_f1": float(f1),
            "per_class": per_class, "confusion_matrix": matrix.tolist(), "roc_auc": auc, "sample_count": len(labels)}
