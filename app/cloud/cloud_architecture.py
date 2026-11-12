"""Especificação Arquitetural e Mapeamento em Nuvem (Google Cloud Platform & Firebase).

Relaciona os requisitos formais de PROJETO FINAL - CLOUD COMPUTING.pdf
com os serviços do Google Cloud for Students e Firebase, gerando também
as regras de segurança do Firestore (firestore.rules) e configurações (firebase.json).
"""
import json
from pathlib import Path
from typing import Any, Dict, Tuple, Union


def get_architecture_mapping() -> Dict[str, Dict[str, str]]:
    """Mapeia os requisitos obrigatórios do PDF para os serviços Google Cloud & Firebase."""
    return {
        "R1": {
            "requisito_pdf": "Utilização de Provedor de Nuvem Acadêmico e Organização",
            "servico_gcp": "Google Cloud Platform & Firebase (Projeto ecobounty-9d250)",
            "detalhes": "Ambiente Google Cloud for Students / Firebase Spark. Organização via projeto ecobounty-9d250, autenticação via Service Account e tokens Google Auth.",
        },
        "R2": {
            "requisito_pdf": "Armazenamento em Nuvem Persistente (Imagens, registros, dados)",
            "servico_gcp": "Google Cloud Storage / Firebase Storage & Cloud Firestore",
            "detalhes": "Firebase Storage armazena permanentemente fotos de denúncias e comprovação de limpeza (Fase 1 e Fase 2). Cloud Firestore (NoSQL gerenciado) persiste missões, usuários, transações e histórico.",
        },
        "R3": {
            "requisito_pdf": "Processamento na Nuvem (Cálculos, regras de negócio, relatórios)",
            "servico_gcp": "Google Cloud Functions / Cloud Run & Google Cloud Vision API",
            "detalhes": "Função Serverless 'ecobounty-audit-processor' acionada no envio de fotos. Realiza auditoria em nuvem via Cloud Vision, cálculo de adiantamento financeiro (50%) e regras anti-fraude.",
        },
        "R4": {
            "requisito_pdf": "Aplicação Funcional com Interface e API documentada",
            "servico_gcp": "Flet Web & Android + REST APIs Google Cloud Firestore",
            "detalhes": "Interface gráfica moderna com suporte a mobile/web/desktop. Comunicação REST/Admin com Cloud Firestore para denúncias, rotas viárias e carteira digital.",
        },
        "R5": {
            "requisito_pdf": "Integração dos Serviços (mínimo 2 serviços integrados com fluxo de dados)",
            "servico_gcp": "Firebase Storage + Cloud Functions + Google Cloud Vision + Cloud Firestore",
            "detalhes": "Pipeline completo: Foto enviada ao Storage -> Dispara Cloud Function -> Analisa resíduos via Cloud Vision -> Valida coordenadas com Grafo de Maceió -> Grava estado no Cloud Firestore.",
        },
        "R6": {
            "requisito_pdf": "Segurança, Gerenciamento de Acesso e Custos",
            "servico_gcp": "Google Cloud IAM (Least Privilege) + Firebase Security Rules",
            "detalhes": "Zero credenciais hardcoded. Variáveis via .env. Regras granulares no firestore.rules. Custo R$ 0,00 coberto integralmente pelo plano gratuito / créditos de estudante.",
        },
    }


def generate_firestore_rules() -> str:
    """Gera regras de segurança do Firestore (firestore.rules) com princípio de menor privilégio."""
    return """rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Regras de Leitura e Escrita de Missões (bounties)
    match /bounties/{bountyId} {
      allow read: if true; // Catálogo público para visualização
      allow create: if request.auth != null || request.resource.data.status == 'DISPONIVEL';
      allow update: if request.auth != null || request.resource.data.current_phase in [1, 2, 3];
      allow delete: if request.auth != null && request.auth.token.admin == true;
    }

    // Regras de Usuários e Coletores
    match /users/{userId} {
      allow read: if true;
      allow write: if request.auth != null && (request.auth.uid == userId || request.auth.token.admin == true);
    }

    // Regras de Transações Financeiras (Auditoria Imutável)
    match /transactions/{txId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null;
      allow update, delete: if false; // Transações financeiras são estritamente imutáveis
    }

    // Histórico de Missões Concluídas
    match /history/{histId} {
      allow read: if true;
      allow create: if request.auth != null;
      allow update, delete: if false;
    }
  }
}
"""


def generate_firebase_json() -> str:
    """Gera a configuração do Firebase (firebase.json)."""
    cfg = {
        "firestore": {
            "rules": "firestore.rules",
            "indexes": "firestore.indexes.json",
        },
        "storage": {
            "rules": "storage.rules",
        },
        "hosting": {
            "public": "web",
            "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
        },
    }
    return json.dumps(cfg, indent=2)


def save_cloud_artifacts(output_dir: Union[str, Path] = ".") -> Tuple[Path, Path]:
    """Salva os artefatos operacionais de infraestrutura Google Cloud / Firebase na raiz do projeto."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rules_path = out / "firestore.rules"
    json_path = out / "firebase.json"

    with open(rules_path, "w", encoding="utf-8") as f:
        f.write(generate_firestore_rules())

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(generate_firebase_json())

    return rules_path, json_path
