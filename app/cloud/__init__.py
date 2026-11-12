"""Módulo de Computação em Nuvem (Google Cloud Platform & Firebase).

Integração com Cloud Firestore, Firebase Storage, Google Cloud Vision e Google Auth
conforme requisitos acadêmicos da disciplina.
"""
from app.cloud.gcp_provider import GoogleCloudProvider, get_gcp_provider
from app.cloud.cloud_architecture import (
    get_architecture_mapping,
    generate_firestore_rules,
    generate_firebase_json,
    save_cloud_artifacts,
)

__all__ = [
    "GoogleCloudProvider",
    "get_gcp_provider",
    "get_architecture_mapping",
    "generate_firestore_rules",
    "generate_firebase_json",
    "save_cloud_artifacts",
]
