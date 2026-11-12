# GUIA DE CONFIGURAÇÃO: GOOGLE CLOUD PLATFORM & FIREBASE (ECOBOUNTY)

**Público-alvo:** Mathias Borges, Allan Gabriel, Kauê Lucas  
**Projeto:** EcoBounty  
**Ambiente:** Google Cloud for Students / Firebase Spark (Projeto `ecobounty-9d250`)

---

## 1. Visão Geral da Arquitetura em Nuvem

O EcoBounty utiliza os serviços integrados da **Google Cloud Platform** e do **Firebase**:
1. **Google Cloud Firestore:** Banco de dados NoSQL de documentos em tempo real para missões (`bounties`), usuários (`users`), transações (`transactions`) e histórico (`history`).
2. **Firebase Cloud Storage / Google Cloud Storage:** Armazenamento seguro de fotos de denúncias e comprovação de limpeza (Fases 1 e 2).
3. **Google Auth:** Provedor de autenticação federada (OAuth 2.0 / Firebase Auth) integrado à interface Flet.
4. **Google Cloud Functions / Cloud Run:** Processamento serverless de auditoria (`ecobounty-audit-processor`).
5. **Google Cloud Vision API:** Detecção de rótulos e auditoria visual inteligente de resíduos sólidos.

---

## 2. Configuração de Credenciais e Ambiente

As configurações sensíveis ficam no arquivo `.env` na raiz do projeto (`c:\ecobounty-app\.env`):

```env
# Ativação dos Provedores em Nuvem Google / Firebase
ECOBOUNTY_STORAGE_BACKEND=firebase
ECOBOUNTY_VISION_BACKEND=google

# Projeto Google Cloud e Firebase
GCP_PROJECT_ID=ecobounty-9d250
FIREBASE_STORAGE_BUCKET=ecobounty-9d250.firebasestorage.app
FIREBASE_AUTH_DOMAIN=ecobounty-9d250.firebaseapp.com

# Caminho da Service Account Admin SDK
GOOGLE_APPLICATION_CREDENTIALS=ecobounty-9d250-firebase-adminsdk-fbsvc-b74d254557.json
```

> **Resiliência Offline:** O EcoBounty possui um **Modo Offline/Simulado de Alta Fidelidade** com cache in-memory e SQLite local. Mesmo sem conexão ativa com o Google Cloud, todas as telas, fluxos de login e 100% dos testes unitários funcionam sem interrupção.

---

## 3. Arquivos de Configuração Operacional do Firebase

Os arquivos operacionais do Firebase ficam localizados na **raiz do projeto** (`c:\ecobounty-app\`):
- `firestore.rules`: Regras de segurança de acesso com menor privilégio para as coleções do Cloud Firestore.
- `firebase.json`: Configuração do Firebase CLI para emuladores, Firestore, Storage e Hosting.
- `firebaseConfig.py` e `firebaseConfig.js`: Configurações de inicialização do cliente Firebase.

Para realizar deploy das regras com a Firebase CLI:
```bash
firebase deploy --only firestore:rules
```

---

## 4. Comandos Úteis para Apresentação e Demonstração

### Rodar a Demonstração Completa ao Vivo (CLI):
```bash
python scripts/demo_algoritmos_nuvem.py
```
*Mostra todas as Estruturas de Dados, Tabelas Hash, Dijkstra em Maceió e os 4 Algoritmos de Ordenação sincronizados com o GCP.*

### Regerar os Gráficos de Alta Resolução (Matplotlib):
```bash
python scripts/gerar_graficos_apresentacao.py
```
*Gera os arquivos `Entregas/benchmark_ordenacao.png` e `Entregas/grafo_maceio_rotas.png` e exporta as regras para a raiz do projeto.*

### Executar a Suíte Completa de 103 Testes Automatizados:
```bash
python -m pytest -v
```

### Iniciar o Aplicativo EcoBounty na Web:
```bash
python -m app.main
```
Acesse no navegador: `http://localhost:8550`
